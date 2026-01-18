# Domain Migration: ajaydhungel.me → ajaydhungel.blog

## Test Results

**Date:** $(date)
**New Domain:** ajaydhungel.blog

### DNS Status
- ❌ **DNS not resolving yet** - Domain may not be configured or DNS still propagating
- Run: `nslookup ajaydhungel.blog` or `dig ajaydhungel.blog` to check DNS

### Configuration Updates
✅ **All configuration files updated:**
- `config.production.yml` - Updated baseURL to `https://ajaydhungel.blog`
- `static/admin/config.yml` - Updated CMS base_url to `https://ajaydhungel.blog`
- `README.md` - Updated all references
- `CONTENT_EDITING.md` - Updated CMS URL
- `CMS_SETUP.md` - Updated CMS URL

## Next Steps

### 1. Configure DNS
Point `ajaydhungel.blog` to your CloudFront distribution or S3 bucket:

**If using CloudFront:**
- Type: `A` or `CNAME`
- Name: `@` (root domain)
- Value: Your CloudFront distribution domain (e.g., `d1234567890.cloudfront.net`)

**If using S3 directly:**
- Type: `CNAME`
- Name: `@`
- Value: `ajaydhungel.me.s3-website-us-east-1.amazonaws.com`

### 2. Update CloudFront (if applicable)
If you have a CloudFront distribution:
1. Go to AWS Console → CloudFront
2. Find your distribution
3. Add `ajaydhungel.blog` to Alternate Domain Names (CNAMEs)
4. Update SSL certificate to include the new domain

### 3. Verify After DNS Propagation
Once DNS is configured and propagated (usually 15 min - 48 hours):
```bash
# Test domain resolution
dig ajaydhungel.blog

# Test HTTPS
curl -I https://ajaydhungel.blog

# Test CMS
curl -I https://ajaydhungel.blog/admin/
```

### 4. Test CMS
After DNS is working:
1. Visit `https://ajaydhungel.blog/admin/`
2. Login with GitHub
3. Verify OAuth callback works

## Files Changed
- `config.production.yml`
- `static/admin/config.yml`
- `static/admin/index.html` (auto-detection added)
- `README.md`
- `CONTENT_EDITING.md`
- `CMS_SETUP.md`

## Notes
- The site will work from any domain once DNS is configured
- Relative URLs are configured, so assets will load correctly
- CMS will auto-detect domain if base_url is not set, but it's now explicitly set to ajaydhungel.blog
