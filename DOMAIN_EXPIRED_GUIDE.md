# Domain Expired - Temporary Access & Recovery Guide

## Your Site is Still Working!

Even though `ajaydhungel.me` expired, your site is still deployed and accessible via:

### Option 1: S3 Website Endpoint (HTTP only)
```
http://ajaydhungel.me.s3-website-us-east-1.amazonaws.com
```

### Option 2: CloudFront Distribution (HTTPS)
If you have a CloudFront distribution, find the URL with:
```bash
aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='ajaydhungel.me' || contains(Aliases.Items, 'ajaydhungel.me')].DomainName" --output text
```

Or check in AWS Console:
1. Go to CloudFront in AWS Console
2. Find distribution for `ajaydhungel.me`
3. Copy the Distribution Domain Name (e.g., `d1234567890.cloudfront.net`)

## When You Renew Your Domain

### Step 1: Renew the Domain
- Contact your domain registrar
- Renew `ajaydhungel.me`

### Step 2: Update DNS Records
Once renewed, make sure your DNS points to:

**If using CloudFront:**
- Type: `A` or `AAAA` (or `CNAME`)
- Name: `@` (or root domain)
- Value: Your CloudFront distribution domain name

**If using S3 directly:**
- Type: `CNAME`
- Name: `@`
- Value: `ajaydhungel.me.s3-website-us-east-1.amazonaws.com`

### Step 3: Verify Everything Works
- Wait for DNS propagation (can take up to 48 hours, usually much faster)
- Test: `https://ajaydhungel.me`
- Test: `https://ajaydhungel.me/admin/` (CMS)

## Current Configuration Status

✅ **Site is still deployed** - S3 bucket `ajaydhungel.me` is active
✅ **Relative URLs configured** - Site works from any URL
✅ **GitHub Actions** - Still deploying automatically
⚠️ **Domain expired** - Custom domain not accessible until renewed

## Quick Commands to Find Your Site URLs

```bash
# Find S3 website endpoint
aws s3api get-bucket-website --bucket ajaydhungel.me --region us-east-1

# Find CloudFront distribution
aws cloudfront list-distributions --query "DistributionList.Items[*].[Id,DomainName,Comment,Aliases]" --output table

# Check if static website hosting is enabled
aws s3api get-bucket-website --bucket ajaydhungel.me --region us-east-1
```

## Notes

- Your site content is safe - nothing is lost
- All deployments are still working
- Once domain is renewed and DNS is updated, everything will work again
- No code changes needed - just DNS configuration
