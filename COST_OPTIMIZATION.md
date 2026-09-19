# Cost Optimization - Google Cloud Deployment

## Region Selection: US vs India

### Why US Region (us-central1)?

**20% cheaper than India region!**

| Region | Location | e2-medium Cost/Hour | Monthly Cost* | Annual Cost* |
|--------|----------|---------------------|---------------|--------------|
| **us-central1** | Iowa, USA | **$0.0268** | **$3.48** | **$41.76** |
| us-east1 | South Carolina | $0.0268 | $3.48 | $41.76 |
| us-west1 | Oregon | $0.0335 | $4.36 | $52.32 |
| asia-south1 | Mumbai, India | $0.0335 | $4.36 | $52.32 |

*Based on 130 hours/month (6.5 hours/day × 20 trading days)

### Cost Breakdown (us-central1)

| Service | Monthly Cost |
|---------|--------------|
| Compute Engine (e2-medium, 130 hrs) | **$3.48** |
| Persistent Disk (20GB Standard) | $0.80 |
| Cloud Logging (5GB) | $0.50 |
| Secret Manager (5 secrets) | $0.18 |
| Cloud Scheduler (2 jobs) | $0.20 |
| Network Egress (1GB) | $0.12 |
| **Total** | **~$5.28/month** |

**Annual Estimate:** ~$63.36/year

---

## Network Latency Impact

### Does it matter for Indian markets?

**No significant impact because:**

1. **Angel One API servers** are globally accessible
2. **Market data delay** is already 1-2 seconds (exchange → broker → API)
3. **US-India latency**: ~200-300ms (negligible vs market data delays)
4. **Order execution**: Not high-frequency trading, operates on minute-level decisions
5. **WebSocket connection**: Stable with auto-reconnect

### Latency Comparison

| Connection | Latency |
|------------|---------|
| India VM → Angel One API | ~10-50ms |
| **US VM → Angel One API** | **~200-300ms** |
| **Difference** | **~250ms** |
| **Market data update frequency** | **1-5 seconds** |

**Verdict:** 250ms difference is **negligible** for non-HFT trading.

---

## Cost Savings Strategies

### 1. Auto-Shutdown (Already Implemented) ✅

| Configuration | Monthly Hours | Monthly Cost | Annual Cost |
|---------------|---------------|--------------|-------------|
| 24/7 Running | 730 hrs | ~$19.56 | ~$234.72 |
| **Trading Hours Only** | **130 hrs** | **$3.48** | **$41.76** |
| **Savings** | - | **-$16.08** | **-$192.96** |

**82% cost reduction!**

### 2. Machine Type Optimization

| Machine Type | vCPU | RAM | Cost/Hour | Monthly Cost* |
|--------------|------|-----|-----------|---------------|
| e2-micro | 0.25-2 | 1GB | $0.0067 | $0.87 | ❌ Too small |
| e2-small | 0.5-2 | 2GB | $0.0134 | $1.74 | ⚠️ Minimal only |
| **e2-medium** | **1-2** | **4GB** | **$0.0268** | **$3.48** | ✅ **Recommended** |
| e2-standard-2 | 2 | 8GB | $0.0536 | $6.97 | ⚠️ If needed |
| e2-standard-4 | 4 | 16GB | $0.1072 | $13.94 | ❌ Overkill |

*Based on 130 hours/month

**Recommendation:** Start with **e2-medium**, upgrade to e2-standard-2 only if needed.

### 3. Committed Use Discounts

| Commitment | Discount | Effective Cost/Hour | Monthly Cost* | Annual Cost* |
|------------|----------|---------------------|---------------|--------------|
| On-Demand | 0% | $0.0268 | $3.48 | $41.76 |
| **1-Year** | **37%** | **$0.0169** | **$2.19** | **$26.28** |
| **3-Year** | **55%** | **$0.0121** | **$1.57** | **$18.84** |

*Based on 130 hours/month

**💡 Recommendation:** 
- **First 6 months:** Use on-demand (paper trading validation)
- **After validation:** Switch to 1-year commitment for 37% savings

**Annual savings with 1-year commitment:** $15.48/year  
**Annual savings with 3-year commitment:** $22.92/year

### 4. Preemptible VMs (Not Recommended)

| Type | Cost Savings | Reliability | Suitable? |
|------|--------------|-------------|-----------|
| Standard VM | Base | 99.9% uptime | ✅ Yes |
| Preemptible | -70% | Can terminate anytime | ❌ No |

**Why not?** Trading requires guaranteed uptime during market hours.

### 5. Storage Optimization

| Storage Type | Monthly Cost (20GB) | Performance | Recommended |
|--------------|---------------------|-------------|-------------|
| **Standard PD** | **$0.80** | Good | ✅ **Yes** |
| Balanced PD | $2.00 | Better | ⚠️ Not needed |
| SSD PD | $3.40 | Best | ❌ Overkill |

**Recommendation:** Standard Persistent Disk is sufficient for SQLite database.

### 6. Logging & Monitoring Optimization

| Optimization | Monthly Savings |
|--------------|-----------------|
| Log retention: 30 days → 7 days | $0.30 |
| Disable debug logs | $0.20 |
| Aggregate metrics | $0.10 |
| **Total Savings** | **$0.60/month** |

---

## Maximum Cost Optimization

### Scenario: Paper Trading (6 months)

| Item | Standard | Optimized | Savings |
|------|----------|-----------|---------|
| VM (e2-medium) | $3.48 | $3.48 | $0 |
| Storage (20GB → 10GB) | $0.80 | $0.40 | $0.40 |
| Logging (optimized) | $0.50 | $0.20 | $0.30 |
| Secret Manager | $0.18 | $0.18 | $0 |
| Scheduler | $0.20 | $0.20 | $0 |
| Network | $0.12 | $0.12 | $0 |
| **Monthly Total** | **$5.28** | **$4.58** | **$0.70** |
| **6-Month Total** | **$31.68** | **$27.48** | **$4.20** |

### Scenario: Live Trading with Commitment (1 year)

| Item | Standard | With 1-Yr Commit | Savings |
|------|----------|------------------|---------|
| VM (e2-medium) | $3.48 | $2.19 | $1.29 |
| Storage | $0.80 | $0.80 | $0 |
| Logging | $0.50 | $0.50 | $0 |
| Secret Manager | $0.18 | $0.18 | $0 |
| Scheduler | $0.20 | $0.20 | $0 |
| Network | $0.12 | $0.12 | $0 |
| **Monthly Total** | **$5.28** | **$3.99** | **$1.29** |
| **Annual Total** | **$63.36** | **$47.88** | **$15.48** |

---

## Cost Comparison: DIY vs Alternatives

### Running on Google Cloud (This Setup)

**Monthly Cost:** $5.28  
**Annual Cost:** $63.36  

**Pros:**
- ✅ Full control
- ✅ Automated start/stop
- ✅ Scalable
- ✅ Pay only for usage (6.5 hrs/day)
- ✅ Professional infrastructure

### Alternative: Local PC (Always On)

**Monthly Electricity Cost:** ~$10-20  
**Annual Cost:** $120-240  

**Cons:**
- ❌ Internet dependency
- ❌ Power cuts = missed trades
- ❌ No auto-restart
- ❌ Maintenance overhead

**Verdict:** Google Cloud is **cheaper and more reliable**.

### Alternative: VPS (Always On)

**Monthly Cost:** $5-10 (DigitalOcean, Linode)  

**Cons:**
- ❌ Runs 24/7 (wasted 17.5 hours/day)
- ❌ No Google Cloud integration
- ❌ Manual management

**Verdict:** Google Cloud with auto-shutdown is **comparable or cheaper**.

### Alternative: Serverless (Cloud Run, Lambda)

**Not suitable because:**
- ❌ No persistent WebSocket connections
- ❌ Stateless (position tracking difficult)
- ❌ 60-minute timeout
- ❌ Cold start delays

**Verdict:** Compute Engine is **the right choice**.

---

## Cost Monitoring & Alerts

### Setup Budget Alerts

```bash
# Create budget alert at $10/month
gcloud billing budgets create \
    --billing-account=YOUR_BILLING_ACCOUNT_ID \
    --display-name="Algo Trading Budget" \
    --budget-amount=10 \
    --threshold-rule=percent=50 \
    --threshold-rule=percent=90 \
    --threshold-rule=percent=100
```

### Daily Cost Check

```bash
# View current month costs
gcloud billing projects describe YOUR_PROJECT_ID --format=json | \
    jq -r '.billingAccountName'

# Or check in Cloud Console:
# https://console.cloud.google.com/billing
```

---

## Summary: Recommended Configuration

### For Paper Trading (First 6 months)

| Configuration | Choice | Monthly Cost |
|---------------|--------|--------------|
| Region | **us-central1-a** | - |
| Machine Type | **e2-medium** | $3.48 |
| Storage | **20GB Standard PD** | $0.80 |
| Running Hours | **130 hrs/month** | - |
| Commitment | **None** (on-demand) | - |
| **Total** | | **$5.28/month** |

**Annual Cost:** ~$63.36

### For Live Trading (After validation)

| Configuration | Choice | Monthly Cost |
|---------------|--------|--------------|
| Region | **us-central1-a** | - |
| Machine Type | **e2-medium** | $2.19 |
| Storage | **20GB Standard PD** | $0.80 |
| Running Hours | **130 hrs/month** | - |
| Commitment | **1-Year** (37% discount) | - |
| **Total** | | **$3.99/month** |

**Annual Cost:** ~$47.88 (saves $15.48/year)

---

## Cost vs Value

### Monthly Cost Breakdown

| Cost | What You Get |
|------|--------------|
| **$5.28/month** | Professional-grade trading infrastructure |
| ($0.26/day) | 99.9% uptime guarantee |
| ($0.04/hour) | Automated start/stop |
| | Real-time market data |
| | Position monitoring |
| | Risk management |
| | Database backups |
| | Cloud logging |
| | Telegram notifications |
| | Zero manual intervention |

**ROI:** If system generates just 1 profitable trade/month (₹500 profit), it pays for itself 95x over!

---

## Action Items

### Immediate (Before Deployment)

- [x] Select **us-central1-a** region (20% cheaper than India)
- [x] Choose **e2-medium** machine type
- [x] Enable auto-shutdown (82% cost savings)
- [x] Setup budget alerts at $10/month

### After 6 Months (Post-Validation)

- [ ] Evaluate performance on e2-medium
- [ ] Consider 1-year commitment for 37% discount
- [ ] Optimize storage (reduce from 20GB to 10GB if possible)
- [ ] Review logging retention (30 days → 7 days)

### Optional Optimizations

- [ ] Reduce boot disk to 15GB if sufficient
- [ ] Disable Cloud Logging debug level
- [ ] Archive old database backups to Cloud Storage (cheaper)
- [ ] Use Cloud SQL only if scaling beyond single instance

---

## Conclusion

**Selected Configuration:**
- **Region:** us-central1-a (Iowa, USA)
- **Cost:** $5.28/month (~₹440/month at ₹83/$)
- **Savings vs 24/7:** 82% reduction
- **Savings vs India region:** 20% reduction
- **Network impact:** Negligible (<300ms latency)

**Total First-Year Cost:** ~$63.36

**After one profitable trade:** System pays for itself! 🎯

---

**Deploy with confidence - you're getting the best value!**
