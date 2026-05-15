package io.github.xkitsios;

import com.github.luben.zstd.Zstd;

import java.io.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class WARP {

    static final java.util.concurrent.ConcurrentHashMap<BucketKey, BucketStat> MODEL = new java.util.concurrent.ConcurrentHashMap<>();

    static BucketKey featurize(SuggestStats s, MixProbeStats m, double epsilonPct) {

        int epsBin;

        int rhoBin;
        if (s.rho < 0.9)        rhoBin = (int)(s.rho * 10);
        else if (s.rho < 0.99)   rhoBin = 10; // 0.90 - 0.99
        else if (s.rho < 0.999)  rhoBin = 11; // 0.99 - 0.999 (SPX 常见)
        else                     rhoBin = 12; // 0.999+ (BTC/Pressure 常见)


        double nz = Math.min(s.nzRateDelta, s.nzRateRls);
        int nzBin = (nz < 0.001) ? 0 : (nz < 0.005) ? 1 : (nz < 0.02) ? 2 : 3;


        double sr = m.segRate();
        int segBin = (sr < 0.005) ? 0 : (sr < 0.02) ? 1 : (sr < 0.1) ? 2 : 3;

        return new BucketKey(rhoBin, nzBin, segBin, s.evenlySpaced ? 1 : 0, epsBin);
    }





    static MixProbeStats mixProbe(List<Point> points, double epsilon, int k) {
        int K = Math.min(points.size(), k);
        if (K <= 2) return new MixProbeStats(K, Math.max(1, K-1), 1, 1);

        java.util.HashSet<Integer> bSet = new java.util.HashSet<>();
        java.util.HashSet<Integer> slopeSet = new java.util.HashSet<>();

        int segCount = 0;
        int idx = 0;
        while (idx < K) {

            Seg segCeil = createSegProbe(points, idx, K, epsilon, 1);
            Seg segFloor = createSegProbe(points, idx, K, epsilon, 2);

            Seg chosen;
            if (segCeil.nextIdx > segFloor.nextIdx) chosen = segCeil;
            else if (segCeil.nextIdx < segFloor.nextIdx) chosen = segFloor;
            else {
                double v0 = points.get(idx).getValue();
                chosen = (Math.round(v0 / epsilon) == Math.ceil(v0 / epsilon)) ? segFloor : segCeil;
            }

            segCount++;
            bSet.add(chosen.bQ);
            slopeSet.add(chosen.aQ);

            idx = chosen.nextIdx;
        }

        return new MixProbeStats(K, segCount, bSet.size(), slopeSet.size());
    }

    static class Seg {
        final int nextIdx;
        final int bQ; // quantized b/epsilon as int
        final int aQ; // quantized slope bucket
        Seg(int nextIdx, int bQ, int aQ) { this.nextIdx = nextIdx; this.bQ = bQ; this.aQ = aQ; }
    }

    static double quantizeB(double value, double epsilon, int mode) {
        if (mode == 1) return Math.ceil(value / epsilon) * epsilon;
        if (mode == 2) return Math.floor(value / epsilon) * epsilon;
        return Math.round(value / epsilon) * epsilon;
    }

    static Seg createSegProbe(List<Point> pts, int start, int endExclusive, double epsilon, int qMode) {
        long t0 = pts.get(start).getTimestamp();
        double b = quantizeB(pts.get(start).getValue(), epsilon, qMode);
        int bQ = (int)Math.round(b / epsilon);

        if (start + 1 >= endExclusive) {
            return new Seg(start + 1, bQ, 0);
        }

        long t1 = pts.get(start + 1).getTimestamp();
        double v1 = pts.get(start + 1).getValue();
        double aMax = ((v1 + epsilon) - b) / (double)(t1 - t0);
        double aMin = ((v1 - epsilon) - b) / (double)(t1 - t0);

        int idx = start + 2;
        for (; idx < endExclusive; idx++) {
            long ti = pts.get(idx).getTimestamp();
            double vi = pts.get(idx).getValue();

            double up = vi + epsilon;
            double down = vi - epsilon;

            double upLim = aMax * (ti - t0) + b;
            double downLim = aMin * (ti - t0) + b;
            if (down > upLim || up < downLim) break;

            if (up < upLim) aMax = Math.max((up - b) / (double)(ti - t0), aMin);
            if (down > downLim) aMin = Math.min((down - b) / (double)(ti - t0), aMax);
        }

        // slope 取区间中点，并做粗量化（避免哈希爆炸）
        double aMid = 0.5 * (aMin + aMax);
        int aQ = (int)Math.round(aMid * 1000.0); // 1e-3 精度桶；你也可按 dt/epsilon 自适应

        return new Seg(idx, bQ, aQ);
    }


    static SuggestStats suggestWStats(List<Point> points, double error, double lambda, Integer wOverride) {
        int n = points.size();


        int checkN = Math.min(n, 8192);
        long[] dtBox = new long[1];
        boolean evenly = quasiEvenlySpaced(points, 0.98, checkN, dtBox);
        double rho = lag1Rho(points, checkN);


        int probeLen = Math.min(n, 20000);
        double nzD = estimateNzRateDelta(points, error, probeLen);
        double nzR = estimateNzRate(points, error, 128, lambda);

        int W = (wOverride != null && wOverride > 0) ? wOverride : suggestW(points, error, lambda);


        boolean fast = (nzR < SPARSE_NZRATE * 2) || (nzD < 0.02) || (W >= n * 0.9);

        return new SuggestStats(W, evenly, rho, nzD, nzR, fast);
    }




    public static byte[] compressAuto(List<Point> points, double error, Integer wOverride) throws Exception {
        if (points == null || points.isEmpty() || error <= 0) throw new Exception("Invalid input or epsilon");
        final double lambda = 0.99;

        // ---- Stage A: 预处理 ----
        SuggestStats s = suggestWStats(points, error, lambda, wOverride);
        MixProbeStats m = mixProbe(points, error, PROBE_K);

        // ---- Stage B: 门控（规则优先，其次学习模型）----
        GateDecision d = ruleGate(s, m);


        System.out.printf(
                "[compressAuto] stats: even=%s rho=%.4f nzD=%.4f nzR=%.4f fast=%s | segRate=%.6f uB=%.4f uS=%.4f | rule=%s%n",
                s.evenlySpaced, s.rho, s.nzRateDelta, s.nzRateRls, s.sparseFastPath,
                m.segRate(), m.uniqueBRate(), m.uniqueSlopeRate(),
                d
        );



        boolean explore = (Math.random() < EXPLORE_P);
        if (explore) d = GateDecision.BOTH;


        if (d == GateDecision.BOTH) {
            GateDecision md = modelPredict(s, m, error);
            if (md != GateDecision.BOTH) d = md;
        }


        // ---- Stage C: 执行 ----
        if (d == GateDecision.ONLY_MIX) {
            byte[] inner = MixCodec.compressMix(points, error);
            ByteArrayOutputStream out = new ByteArrayOutputStream(inner.length + 4);
            out.write(MAGIC_MIX1);
            out.write(inner);
            return out.toByteArray();
        }

        if (d == GateDecision.ONLY_WAP) {
            int W = s.W;
            return compress_WAPSRC(points, error, W);
        }


        CompletableFuture<byte[]> mixF = CompletableFuture.supplyAsync(() -> {
            try {
                byte[] inner = MixCodec.compressMix(points, error);
                ByteArrayOutputStream out = new ByteArrayOutputStream(inner.length + 4);
                out.write(MAGIC_MIX1);
                out.write(inner);
                return out.toByteArray();
            } catch (Exception e) {
                throw new CompletionException(e);
            }
        }, CODEC_EXEC);

        CompletableFuture<byte[]> wapsrcF = CompletableFuture.supplyAsync(() -> {
            try {
                return compress_WAPSRC(points, error, s.W);
            } catch (Exception e) {
                throw new CompletionException(e);
            }
        }, CODEC_EXEC);

        byte[] a4 = null, mx = null;
        Throwable e4 = null, em = null;
        try { a4 = wapsrcF.join(); } catch (CompletionException ce) { e4 = ce.getCause(); }
        try { mx = mixF.join();  } catch (CompletionException ce) { em = ce.getCause(); }

        if (a4 == null && mx == null) {
            throw new Exception("All compressors failed: WAP-SRC=" + (e4!=null?e4.getMessage():"null")
                    + ", MIX=" + (em!=null?em.getMessage():"null"));
        }

        if (a4 != null && mx != null) {
            modelUpdate(s, m, error, mx.length, a4.length);
        }

        byte[] best = null;
        int bestLen = Integer.MAX_VALUE;
        if (a4 != null && a4.length < bestLen) { best = a4; bestLen = a4.length; }
        if (mx != null && mx.length < bestLen) { best = mx; bestLen = mx.length; }

        if (a4 != null && mx != null) {
            int min = Math.min(a4.length, mx.length);
            int max = Math.max(a4.length, mx.length);
            if (max <= (int)Math.ceil(min * 1.03)) {
                return mx;
            }
        }
        return best;
    }


    public static byte[] compress_WAPSRC(List<Point> points, double error, Integer wOverride) throws Exception {
        if (points == null || points.isEmpty() || error <= 0) throw new Exception("Invalid input or epsilon");
        epsilon = error;
        lastTimeStamp = points.get(points.size() - 1).getTimestamp();

        long dt = 0;


        final double epsRes = 2.0 * epsilon;
        final double invEpsRes = 1.0 / epsRes;

        final int W = (wOverride != null && wOverride > 0) ? wOverride : suggestW(points, epsilon, 0.99);

        ByteArrayOutputStream recOut = new ByteArrayOutputStream();
        int recordCount = 0;


        double phi = 0.0, P = 1e6, lambda = 0.99;
        double lastY = 0.0;

        long expectedNextStartTs = points.get(0).getTimestamp();
        final int n = points.size();

        for (int start = 0; start < n; ) {
            int len = Math.min(W, n - start);
            long startTs = points.get(start).getTimestamp();
            double y0 = points.get(start).getValue();

            boolean hasTs  = (recordCount == 0) || (startTs != expectedNextStartTs);
            boolean hasLen = (len != W);


            int q0A = (int) Math.rint((y0 - (phi * lastY)) / epsRes);
            int q0EncA = zigZagEncode(q0A);
            int q0ALen = uvarLen32(q0EncA);

            double phiLocA = phi, PLocA = P;
            double lastYL_A = phi * lastY + q0A * epsRes;
            int nzA = 0, valBytesA = 0, posBytesA = 0, prevA = -1;
            for (int i = start + 1, pos = 0; i < start + len; i++, pos++) {
                double yhat = phiLocA * lastYL_A;
                double e = points.get(i).getValue() - yhat;
                int q = (int) Math.rint(e * invEpsRes);
                if (q != 0) {
                    nzA++;
                    int enc = zigZagEncode(q);
                    valBytesA += uvarLen32(enc);
                    int gap = (prevA < 0) ? pos : (pos - prevA - 1);
                    posBytesA += uvarLen32(gap);
                    prevA = pos;
                }
                double yRecon = yhat + q * epsRes;
                double denom = lambda + lastYL_A * PLocA * lastYL_A;
                double K = (PLocA * lastYL_A) / denom;
                phiLocA += K * (yRecon - yhat);
                PLocA = (PLocA - K * lastYL_A * PLocA) / lambda;
                lastYL_A = yRecon;
            }
            int maskBytesA = Math.max(0, (len - 1 + 7) / 8);
            int bodyBytesA = (nzA == 0) ? 0 : Math.min(maskBytesA + uvarLen32(nzA) + valBytesA, uvarLen32(nzA) + posBytesA + valBytesA);
            int totalA = (hasTs ? uvarLen64(startTs) : 0) + (hasLen ? uvarLen32(len) : 0) + 1 + q0ALen + bodyBytesA;


            int q0D = (int) Math.rint((y0 - lastY) / epsRes);
            int q0EncD = zigZagEncode(q0D);
            int q0DLen = uvarLen32(q0EncD);

            double lastYL_D = lastY + q0D * epsRes;
            int nzD = 0, valBytesD = 0, posBytesD = 0, prevD = -1;
            for (int i = start + 1, pos = 0; i < start + len; i++, pos++) {
                double yhat = lastYL_D;
                double e = points.get(i).getValue() - yhat;
                int q = (int) Math.rint(e * invEpsRes);
                if (q != 0) {
                    nzD++;
                    int enc = zigZagEncode(q);
                    valBytesD += uvarLen32(enc);
                    int gap = (prevD < 0) ? pos : (pos - prevD - 1);
                    posBytesD += uvarLen32(gap);
                    prevD = pos;
                }
                double yRecon = yhat + q * epsRes;
                lastYL_D = yRecon;
            }
            int bodyBytesD = (nzD == 0) ? 0 : Math.min(maskBytesA + uvarLen32(nzD) + valBytesD, uvarLen32(nzD) + posBytesD + valBytesD);
            int totalD = (hasTs ? uvarLen64(startTs) : 0) + (hasLen ? uvarLen32(len) : 0) + 1 + q0DLen + bodyBytesD;


            boolean useDelta = (totalD <= totalA);

            int nz = 0, valBytes = 0, posBytes = 0, prev = -1;
            int q0 = useDelta ? q0D : q0A;
            int q0Enc = useDelta ? q0EncD : q0EncA;
            ArrayList<Integer> nzPos = new ArrayList<>();
            ArrayList<Integer> nzVals = new ArrayList<>();

            double phiAfter = phi, PAfter = P, lastYAfter;

            if (!useDelta) {
                double phiLoc = phi, PLoc = P, lastYL = phi * lastY + q0 * epsRes;
                for (int i = start + 1, pos = 0; i < start + len; i++, pos++) {
                    double yhat = phiLoc * lastYL;
                    int q = (int) Math.rint((points.get(i).getValue() - yhat) * invEpsRes);
                    if (q != 0) {
                        nz++; int enc = zigZagEncode(q);
                        nzPos.add(pos); nzVals.add(enc);
                        valBytes += uvarLen32(enc);
                        int gap = (prev < 0) ? pos : (pos - prev - 1);
                        posBytes += uvarLen32(gap); prev = pos;
                    }
                    double yRecon = yhat + q * epsRes;
                    double denom = lambda + lastYL * PLoc * lastYL;
                    double K = (PLoc * lastYL) / denom;
                    phiLoc += K * (yRecon - yhat);
                    PLoc = (PLoc - K * lastYL * PLoc) / lambda;
                    lastYL = yRecon;
                }
                phiAfter = phiLoc; PAfter = PLoc; lastYAfter = lastYL;
            } else {
                double lastYL = lastY + q0 * epsRes;
                for (int i = start + 1, pos = 0; i < start + len; i++, pos++) {
                    double yhat = lastYL;
                    int q = (int) Math.rint((points.get(i).getValue() - yhat) * invEpsRes);
                    if (q != 0) {
                        nz++; int enc = zigZagEncode(q);
                        nzPos.add(pos); nzVals.add(enc);
                        valBytes += uvarLen32(enc);
                        int gap = (prev < 0) ? pos : (pos - prev - 1);
                        posBytes += uvarLen32(gap); prev = pos;
                    }
                    lastYL = yhat + q * epsRes;
                }
                lastYAfter = lastYL;
            }


            int baseMode;
            if (nz == 0) baseMode = MODE_ZERO;
            else {
                int maskBytes = (len - 1 + 7) / 8;
                int bytesMask   = maskBytes + uvarLen32(nz) + valBytes;
                int bytesSparse = uvarLen32(nz) + posBytes + valBytes;
                baseMode = (bytesMask <= bytesSparse + 1) ? 0 : 1;
            }

            int modeByte = (baseMode & MODE_BASE_MASK) | (useDelta ? FLAG4_PRED_DELTA : 0) | (hasTs ? FLAG4_HAS_TS : 0) | (hasLen ? FLAG4_HAS_LEN : 0);


            int runWins = 1;
            if (baseMode == MODE_ZERO && len == W && q0 == 0) {
                double phiRun = phiAfter, PRun = PAfter, lastYRun = lastYAfter;
                int s2 = start + W;
                while (s2 + W <= n) {
                    double y0_2 = points.get(s2).getValue();
                    int q0_2 = useDelta ? (int) Math.rint((y0_2 - lastYRun) * invEpsRes) : (int) Math.rint((y0_2 - (phiRun * lastYRun)) * invEpsRes);
                    if (q0_2 != 0) break;
                    boolean allZero = true;
                    if (!useDelta) {
                        double phi2 = phiRun, P2 = PRun, ly2 = phiRun * lastYRun;
                        for (int i = s2 + 1; i < s2 + W; i++) {
                            double yh = phi2 * ly2;
                            int q = (int) Math.rint((points.get(i).getValue() - yh) * invEpsRes);
                            if (q != 0) { allZero = false; break; }
                            double yr = yh;
                            double den = lambda + ly2 * P2 * ly2;
                            double K = (P2 * ly2) / den;
                            phi2 += K * (yr - yh); P2 = (P2 - K * ly2 * P2) / lambda; ly2 = yr;
                        }
                        if (!allZero) break;
                        phiRun = phi2; PRun = P2; lastYRun = ly2;
                    } else {
                        double ly2 = lastYRun;
                        for (int i = s2 + 1; i < s2 + W; i++) {
                            if ((int) Math.rint((points.get(i).getValue() - ly2) * invEpsRes) != 0) { allZero = false; break; }
                        }
                        if (!allZero) break;
                        lastYRun = ly2;
                    }
                    runWins++; s2 += W;
                }
                if (runWins > 1) {
                    modeByte |= FLAG4_ZERO_RLE;
                    if (!useDelta) { phiAfter = phiRun; PAfter = PRun; }
                    lastYAfter = lastYRun;
                }
            }


            recOut.write(modeByte);
            if (hasTs) UIntEncoder.write(startTs, recOut);
            if (hasLen) VariableByteEncoder.write(len, recOut);
            VariableByteEncoder.write(q0Enc, recOut);

            if ((modeByte & FLAG4_ZERO_RLE) != 0) {
                VariableByteEncoder.write(runWins, recOut);
                start += runWins * W;
                expectedNextStartTs = startTs + (long) runWins * W * dt;
            } else {
                if (baseMode == 0) { // Mask
                    int maskBytes = (len - 1 + 7) / 8;
                    byte[] mask = new byte[maskBytes];
                    for (int p : nzPos) setMaskBit(mask, p);
                    recOut.write(mask);
                    VariableByteEncoder.write(nz, recOut);
                    for (int v : nzVals) VariableByteEncoder.write(v, recOut);
                } else if (baseMode == 1) { // Sparse
                    VariableByteEncoder.write(nz, recOut);
                    int prP = -1;
                    for (int p : nzPos) {
                        VariableByteEncoder.write(p - prP - 1, recOut);
                        prP = p;
                    }
                    for (int v : nzVals) VariableByteEncoder.write(v, recOut);
                }
                start += len;
                expectedNextStartTs = startTs + (long) len * dt;
            }

            if (!useDelta) { phi = phiAfter; P = PAfter; }
            lastY = lastYAfter;
            recordCount++;
        }

        // 组装并 Zstd 压缩
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        out.write(MAGIC_WAPSRC);
        writeDouble(out, epsilon);
        writeDouble(out, 2.0 * epsilon);
        VariableByteEncoder.write(W, out);
        VariableByteEncoder.write(recordCount, out);
        UIntEncoder.write(dt, out);
        UIntEncoder.write(lastTimeStamp, out);
        out.write(recOut.toByteArray());

        return Zstd.compress(out.toByteArray(), ZSTD_LEVEL);
    }



    static int suggestW(List<Point> pts, double epsilon, double lambda) {
        if (pts == null || pts.size() < 300) return MIN_W;

        long[] dtBox = new long[1];
        if (!quasiEvenlySpaced(pts, 0.98, 4096, dtBox)) return MIN_W;

        double rho = lag1Rho(pts, 4096);
        double Lr = (rho > 0) ? 1.0 / (1.0 - Math.min(0.999, rho)) : 1.0;
        double Lλ = 1.0 / (1.0 - lambda);
        double L = Math.max(Lr, Lλ);

        int n = pts.size();
        int maxW = Math.max(MIN_W, align128Down(n));


        int Wprobe = Math.min(131_072, n);
        double nzRateRls   = estimateNzRate(pts, epsilon, Wprobe, lambda);
        double nzRateDelta = estimateNzRateDelta(pts, epsilon, Math.min(200_000, n));
        if ((nzRateRls >= 0 && nzRateRls < SPARSE_NZRATE * 2) ||   // 放宽到 0.2%
                nzRateDelta < 0.02 ||                                 // Delta 非零率 < 2%
                (nzRateDelta < 0.05 && n >= 200_000)) {               // 大序列稍微放宽
            return maxW;  // 直接用最大窗口，退化为全局 Delta + 稀疏
        }


        List<Integer> coarse = buildCandidates(n);
        WBpp best = null;
        best = evaluateAndUpdateBestConcurrent(pts, epsilon, lambda, coarse, best);


        List<Integer> refine = buildRefineCandidates(n, best != null ? best.W : MIN_W);
        best = evaluateAndUpdateBestConcurrent(pts, epsilon, lambda, refine, best);

        // 谷底保护区并发（仅在可信区间内独立取最优）
        List<Integer> trusted = new ArrayList<>();
        for (int W = MIN_W; W <= Math.min(VALLEY_GUARD_MAX_W, maxW); W += 256) trusted.add(W);
        WBpp trustBest = evaluateBestOnlyConcurrent(pts, epsilon, lambda, trusted);

        if (trustBest != null && trustBest.bpp + 1e-12 < best.bpp * (1.0 - VALLEY_GUARD_MARGIN)) {
            return trustBest.W;
        }
        return Math.max(MIN_W, Math.min(best.W, maxW));
    }



    // 仅在 candidates 内部取最优（不与外部 best 比较）
    private static WBpp evaluateBestOnlyConcurrent(
            List<Point> pts, double epsilon, double lambda,
            List<Integer> candidates) {

        if (candidates == null || candidates.isEmpty()) return null;
        CompletionService<WBpp> cs = new ExecutorCompletionService<>(CODEC_EXEC);
        for (int W : candidates) {
            cs.submit(() -> new WBpp(W, estimateBppForW(pts, epsilon, lambda, W)));
        }
        WBpp best = null;
        try {
            for (int i = 0; i < candidates.size(); i++) {
                WBpp r = cs.take().get();
                best = better(best, r);
            }
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        } catch (ExecutionException ee) {

        }
        return best;
    }


    static List<Integer> buildCandidates(int n) {
        int maxW = Math.max(MIN_W, align128Down(n));
        ArrayList<Integer> list = new ArrayList<>();
        if (maxW <= MIN_W) { list.add(maxW); return list; }

        long W = align128Up(MIN_W);
        int last = -1;
        while (W < maxW) {
            if ((int)W != last) list.add((int)W);
            last = (int)W;
            long next = (long) Math.ceil(W * 1.6);               // 几何步进（1.6）
            if (next <= W) break;
            W = align128Up((int)Math.min(next, maxW));
        }
        if (list.isEmpty() || list.get(list.size() - 1) != maxW) list.add(maxW); // 包含最大
        return list;
    }


    static double lag1Rho(List<Point> pts, int maxN) {
        int m = Math.min(pts.size(), Math.max(3, maxN));
        if (m < 3) return 0.0;
        double sum = 0, sum2 = 0;
        for (int i = 0; i < m; i++) {
            double y = pts.get(i).getValue();
            sum += y; sum2 += y * y;
        }
        double mean = sum / m;
        double var = sum2 / m - mean * mean;
        if (var <= 0) return 0.0;

        double cov = 0.0;
        for (int i = 1; i < m; i++) {
            double y0 = pts.get(i - 1).getValue() - mean;
            double y1 = pts.get(i).getValue() - mean;
            cov += y0 * y1;
        }
        cov /= (m - 1);
        double rho = cov / var;
        if (rho > 0.99) rho = 0.99 ;
        if (rho < -0.99) rho = -0.99;
        return rho;
    }







}