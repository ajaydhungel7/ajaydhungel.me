# DNS Troubleshooting for ajaydhungel.blog

## Current Status
❌ DNS not resolving yet

## Common Issues & Solutions

### 1. DNS Record Type

**For CloudFront, you need:**
- **Type:** `CNAME` (recommended) or `A` (if using Route 53 Alias)
- **Name:** `@` (root domain) or leave blank
- **Value:** Your CloudFront distribution domain (e.g., `d1234567890abc.cloudfront.net`)

**Important:** Get the exact CloudFront domain from AWS Console:
- CloudFront → Your Distribution → Domain Name
- It looks like: `d1234567890abc.cloudfront.net`

### 2. Check Your DNS Records

In your registrar (Spaceship):
1. Go to DNS Management
2. Verify the CNAME record exists
3. Make sure it points to the CloudFront domain (not S3)
4. Check for typos in the CloudFront domain

### 3. CloudFront Configuration

Verify in AWS Console:
- ✅ Distribution is **Deployed** (not "In Progress")
- ✅ `ajaydhungel.blog` is in **Alternate Domain Names (CNAMEs)**
- ✅ SSL certificate is **Issued** and attached
- ✅ **Viewer Protocol Policy**: Redirect HTTP to HTTPS (recommended)

### 4. DNS Propagation

DNS changes can take:
- **Minimum:** 5-15 minutes
- **Typical:** 1-4 hours
- **Maximum:** 48 hours

**Check propagation:**
```bash
# Check from different DNS servers
dig @8.8.8.8 ajaydhungel.blog
dig @1.1.1.1 ajaydhungel.blog
nslookup ajaydhungel.blog

# Or use online tools:
# https://dnschecker.org
# https://www.whatsmydns.net
```

### 5. Common Mistakes

❌ **Pointing to S3 instead of CloudFront**
- Old: `ajaydhungel.me.s3-website-us-east-1.amazonaws.com`
- New: `d1234567890abc.cloudfront.net`

❌ **Wrong record type**
- Should be `CNAME` for CloudFront
- Not `A` record (unless using Route 53 Alias)

❌ **CloudFront not deployed**
- Distribution must be "Deployed" status
- Can take 15-30 minutes after creation

❌ **Domain not in CloudFront CNAMEs**
- Must add `ajaydhungel.blog` to Alternate Domain Names
- Must match exactly (no www, no trailing dot)

## Step-by-Step Verification

### Step 1: Get CloudFront Domain
```bash
aws cloudfront list-distributions \
  --query "DistributionList.Items[*].[Id,DomainName,Aliases.Items,Status]" \
  --output table
```

Or in AWS Console:
- CloudFront → Your Distribution → Copy "Domain Name"

### Step 2: Verify DNS Record
In Spaceship DNS:
- Record Type: `CNAME`
- Name: `@` or blank
- Value: `d1234567890abc.cloudfront.net` (your CloudFront domain)
- TTL: 3600 (or default)

### Step 3: Verify CloudFront
- Status: Deployed
- Alternate Domain Names: Contains `ajaydhungel.blog`
- SSL Certificate: Issued and selected
- Origin: Points to S3 website endpoint

### Step 4: Wait and Test
```bash
# Test DNS resolution
dig ajaydhungel.blog +short

# Should return CloudFront domain
# If empty, DNS not propagated yet

# Test HTTP
curl -I http://ajaydhungel.blog

# Test HTTPS
curl -I https://ajaydhungel.blog
```

## Quick Checklist

- [ ] CloudFront distribution created and deployed
- [ ] `ajaydhungel.blog` added to CloudFront CNAMEs
- [ ] SSL certificate issued and attached to distribution
- [ ] DNS CNAME record points to CloudFront domain (not S3)
- [ ] Waited at least 15-30 minutes for propagation
- [ ] Checked DNS from multiple locations

## Still Not Working?

1. **Double-check CloudFront domain** - Copy it exactly from AWS Console
2. **Verify DNS record** - Make sure it's saved correctly in Spaceship
3. **Check CloudFront status** - Must be "Deployed"
4. **Wait longer** - Sometimes takes 1-2 hours
5. **Try different DNS servers** - Use 8.8.8.8, 1.1.1.1, or online tools

## Need Help?

Share:
- Your CloudFront distribution domain
- Your current DNS record (what it points to)
- CloudFront status (Deployed/In Progress)

And I can help troubleshoot further!
