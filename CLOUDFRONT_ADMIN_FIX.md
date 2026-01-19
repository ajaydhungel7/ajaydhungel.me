# Fix CloudFront Admin Route - Targeted Solution

## Problem
Accessing `https://ajaydhungel.blog/admin/` shows home page instead of CMS.

## Solution: Use CloudFront Function (Recommended)

This only affects `/admin/` requests, not other 404s.

### Step 1: Create CloudFront Function

1. Go to AWS Console → CloudFront → Functions
2. Click **Create Function**
3. Name: `admin-rewrite`
4. Copy this code:

```javascript
function handler(event) {
    var request = event.request;
    var uri = request.uri;
    
    // If accessing /admin/ or /admin, rewrite to /admin/index.html
    if (uri === '/admin/' || uri === '/admin') {
        request.uri = '/admin/index.html';
    }
    
    return request;
}
```

5. Click **Publish**

### Step 2: Associate Function with Distribution

1. Go to your CloudFront distribution
2. **Behaviors** tab → Edit your behavior
3. Scroll to **CloudFront Functions**
4. **Viewer Request**: Select `admin-rewrite`
5. Save changes
6. Wait for deployment (~15-30 minutes)

## Alternative: Use S3 Website Endpoint

Make sure CloudFront origin is using the **S3 website endpoint** (not REST API):

- ✅ Correct: `ajaydhungel.me.s3-website-us-east-1.amazonaws.com`
- ❌ Wrong: `ajaydhungel.me.s3.amazonaws.com` or `ajaydhungel.me.s3.us-east-1.amazonaws.com`

S3 website endpoints automatically handle directory requests (`/admin/` → `/admin/index.html`).

## Verify Origin Configuration

In CloudFront:
1. **Origins** tab → Select your origin
2. **Origin Domain**: Should be `ajaydhungel.me.s3-website-us-east-1.amazonaws.com`
3. If it's the REST API endpoint, update it to the website endpoint

## Test After Fix

```bash
# Should serve CMS interface
curl -I https://ajaydhungel.blog/admin/

# Should still show 404 for invalid pages
curl -I https://ajaydhungel.blog/invalid-page/
```

## Why This Works

- CloudFront Function only rewrites `/admin/` requests
- Other 404s remain unaffected
- No impact on existing error handling
- Simple and maintainable
