# Blog Posts Feature - Setup Complete! 🎉

You can now create and manage blog posts directly through the CMS!

## What's Been Set Up

✅ **Blog Posts Collection** - Added to CMS at `/admin/`
✅ **Articles Folder** - Created `content/articles/` for storing posts
✅ **CMS Configuration** - Configured with all necessary fields
✅ **Example Post** - Created a sample post to show the format

## How to Create a Blog Post

### Using the CMS (Recommended)

1. **Access CMS**: Go to `https://ajaydhungel.blog/admin/`
2. **Login**: Click "Login with GitHub" and authorize
3. **Create Post**: 
   - Click "Blog Posts" in the sidebar
   - Click "New Blog Post" button
4. **Fill in Details**:
   - **Title**: Your post title
   - **Publish Date**: When to publish (defaults to now)
   - **Draft**: Leave checked to save as draft, uncheck to publish
   - **Author**: Defaults to "Ajay Dhungel"
   - **Description**: Optional SEO description
   - **Tags**: Add tags to organize posts (optional)
   - **Body**: Write your post content in Markdown
5. **Publish**: Click "Publish" to save to GitHub

### Post File Format

Posts are saved as: `content/articles/YYYY-MM-DD-post-title.md`

Example: `content/articles/2024-01-15-my-first-post.md`

## Post Structure

Each post includes:
- **Title** - The post title
- **Date** - Publication date
- **Draft** - Whether it's published or draft
- **Author** - Post author
- **Description** - SEO description
- **Tags** - For categorization
- **Content** - Markdown content

## Where Posts Appear

- **Home Page**: Posts appear in the main articles section (if configured)
- **Articles Page**: Available at `/articles/`
- **Individual Posts**: Each post has its own URL like `/articles/2024-01-15-post-title/`

## Markdown Tips

You can use all Markdown features:
- Headings: `# H1`, `## H2`, `### H3`
- **Bold** and *italic*
- Lists, links, images
- Code blocks
- And more!

## Managing Posts

- **Edit**: Click any post in the CMS to edit
- **Delete**: Use the delete button in the CMS
- **Drafts**: Set `draft: true` to save without publishing

## Next Steps

1. Delete the example post (`content/articles/example-post.md`) once you're ready
2. Create your first real blog post through the CMS!
3. Posts will automatically appear on your site after deployment

Enjoy writing! 📝
