# Ajay's Hugo Profile

Welcome to my personal profile site built with Hugo using the [CharlolaMode theme](https://github.com/charlola/hugo-theme-charlolamode). This repository contains the necessary files to set up and customize your profile. Find this site on (https://ajaydhungel.blog)

## Features

- Responsive design
- Customizable layouts
- Easy integration of social media links
- **Medium Feed Widget** - Automatically displays your latest Medium articles with thumbnails and titles
- Beautiful grid layout with hover effects

## Getting Started

### Prerequisites

Make sure you have [Hugo](https://gohugo.io/getting-started/installation/) and Git installed.

### Clone the Repository

Clone the template repository to your local machine:

```bash
git clone https://github.com/charlola/hugo-theme-charlolamode

```
Install the Theme

Change into the directory and initialize the theme:
```bash
cd your-repo-name
git submodule init
git submodule update
```
Run the Development Server

Run the Hugo development server:

```bash
hugo server
```
Access your profile at http://localhost:1313.

## Content Editing

Your blog page automatically displays your latest Medium articles. The feed is powered by the Medium Feed Widget which:

1. **Fetches your Medium feed** automatically from `https://medium.com/@adhungel2`
2. **Displays articles** with thumbnails, titles, and publication dates in a beautiful grid
3. **Links directly to Medium** - clicking on any article takes you to the full post on Medium
4. **No maintenance needed** - new articles appear automatically when you publish on Medium

To customize the feed:
- Edit the `data-medium-feed="adhungel2"` value in [content/blog/blog.md](content/blog/blog.md) to your Medium username
- Adjust `data-medium-limit="6"` to show more or fewer articles

## Deployment

The site is automatically deployed to AWS S3 via GitHub Actions when you push to the `main` branch.

### Manual Deployment

If you need to deploy manually:

```bash
hugo --environment production
aws s3 sync public/ s3://ajaydhungel.me/ --delete
```
