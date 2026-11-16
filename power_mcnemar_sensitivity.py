import numpy as np
from scipy.stats import binomtest
from scipy.special import gammaln
n=88
# exact two-sided McNemar p for each (b,c)
P=np.ones((n+1,n+1))
for b in range(n+1):
    for c in range(n+1-b):
        m=b+c
        if m: P[b,c]=binomtest(b,m,0.5).pvalue
B,C=np.meshgrid(np.arange(n+1),np.arange(n+1),indexing='ij')
valid=(B+C)<=n
lg=gammaln(n+1)-gammaln(B+1)-gammaln(C+1)-gammaln(n-B-C+1)
def power(d,rd,alpha):
    pb=(d+rd)/2; pc=(d-rd)/2
    if pc<=0: return None
    with np.errstate(all='ignore'):
        lp=lg+B*np.log(pb)+C*np.log(pc)+(n-B-C)*np.log(1-pb-pc)
    pr=np.where(valid,np.exp(lp),0.0)
    return pr[(P<=alpha)&valid&((B+C)>0)].sum()
for alpha in (0.05,0.05/6):
    for d in (0.15,0.25,0.30):
        res=None
        for rd in np.arange(0.04,d-0.005,0.005):
            pw=power(d,rd,alpha)
            if pw is not None and pw>=0.8: res=(round(rd*100,1),round(pw,3));break
        print(f"alpha={alpha:.4f} discordance={d:.2f}: min RD (points) for 80% power = {res}")
# observed
for nm,b,c in (("Qwen dir",21,1),("Qwen ev",20,5),("Gem dir",25,3),("Gem ev",18,2)):
    print(nm,"discordance",(b+c)/n, "RD",(b-c)/n)
