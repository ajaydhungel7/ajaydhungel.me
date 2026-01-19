# S3 Direct DNS Setup - Important Notes

## Current Setup
You've configured `ajaydhungel.blog` to point directly to your S3 bucket via CNAME.

## Important Considerations

### 1. **HTTP Only (No HTTPS)**
⚠️ **S3 website endpoints only support HTTP, not HTTPS.**

- Your site will be accessible at: `http://ajaydhungel.blog` (not `https://`)
- Modern browsers may show "Not Secure" warnings
- Some features (like CMS OAuth) may not work properly without HTTPS

### 2. **Correct S3 Website Endpoint Format**
Your S3 bucket is: `ajaydhungel.me`

The website endpoint should be:
```
ajaydhungel.me.s3-website-us-east-1.amazonaws.com
```

**Make sure your CNAME points to this exact endpoint** (not the REST API endpoint like `ajaydhungel.me.s3.us-east-1.amazonaws.com`)

### 3. **DNS Propagation**
- DNS changes can take 15 minutes to 48 hours to propagate
- Check propagation with: `dig ajaydhungel.blog CNAME`
- Or use online tools like: https://dnschecker.org

### 4. **S3 Bucket Configuration Required**
Make sure your S3 bucket has:
- ✅ Static website hosting enabled
- ✅ Index document: `index.html`
- ✅ Error document: `404.html` (optional)
- ✅ Public read access (bucket policy)

## Recommended: Use CloudFront for HTTPS

For production, consider using CloudFront:
- ✅ Free SSL certificate (HTTPS)
- ✅ Better performance (CDN caching)
- ✅ More secure
- ✅ Works with CMS OAuth

### CloudFront Setup:
1. Create CloudFront distribution
2. Origin: Your S3 bucket website endpoint
3. Add `ajaydhungel.blog` to Alternate Domain Names
4. Request SSL certificate in ACM (us-east-1)
5. Update CNAME to point to CloudFront distribution domain

## Testing Your Setup

Once DNS propagates:

```bash
# Check DNS
dig ajaydhungel.blog CNAME

# Test HTTP (will work)
curl -I http://ajaydhungel.blog

# Test HTTPS (will fail with direct S3)
curl -I https://ajaydhungel.blog
```

## Current Status
- ✅ Domain registered
- ✅ CNAME record added
- ⏳ Waiting for DNS propagation
- ⚠️ Will be HTTP only (no HTTPS)

## Next Steps
1. Wait for DNS propagation (check every 15-30 minutes)
2. Test: `http://ajaydhungel.blog` (note: HTTP, not HTTPS)
3. Consider setting up CloudFront for HTTPS support
