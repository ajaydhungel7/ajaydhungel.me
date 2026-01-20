// Multi-source Feed Widget
// Fetches and displays articles from multiple sources with thumbnails and titles

async function loadMultipleFeedsWidget(config) {
  try {
    const { sources, containerId, limit = null } = config;
    
    if (!sources || sources.length === 0) {
      console.error('No feed sources provided');
      return;
    }
    
    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`Container with id "${containerId}" not found`);
      return;
    }
    
    container.innerHTML = '';
    
    // Fetch all articles from all sources
    const allArticles = [];
    
    for (const source of sources) {
      try {
        let feedUrl;
        
        if (source.type === 'medium') {
          feedUrl = `https://api.rss2json.com/v1/api.json?rss_url=https://medium.com/feed/@${source.username}`;
        } else if (source.type === 'rss') {
          feedUrl = `https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(source.url)}`;
        }
        
        if (!feedUrl) continue;
        
        const response = await fetch(feedUrl);
        if (!response.ok) throw new Error(`Failed to fetch ${source.name} feed`);
        
        const data = await response.json();
        if (data.items) {
          data.items.forEach(item => {
            allArticles.push({
              ...item,
              source: source.name
            });
          });
        }
      } catch (error) {
        console.error(`Error loading ${source.name} feed:`, error);
      }
    }
    
    // Sort by date (newest first)
    allArticles.sort((a, b) => new Date(b.pubDate) - new Date(a.pubDate));
    
    // Deduplicate by title
    const seenTitles = new Set();
    const uniqueArticles = allArticles.filter(article => {
      if (seenTitles.has(article.title)) {
        return false;
      }
      seenTitles.add(article.title);
      return true;
    });
    
    // Limit if specified
    const articles = limit ? uniqueArticles.slice(0, limit) : uniqueArticles;
    
    const feedGrid = document.createElement('div');
    feedGrid.className = 'medium-feed-grid';
    
    articles.forEach(article => {
      const thumbnail = extractImageFromContent(article.content);
      const pubDate = new Date(article.pubDate).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
      
      const article_el = document.createElement('a');
      article_el.href = article.link;
      article_el.target = '_blank';
      article_el.rel = 'noopener noreferrer';
      article_el.className = 'medium-feed-item';
      
      article_el.innerHTML = `
        <div class="medium-feed-card">
          ${thumbnail ? `<div class="medium-feed-image"><img src="${thumbnail}" alt="${article.title}" loading="lazy"></div>` : ''}
          <div class="medium-feed-content">
            <h3 class="medium-feed-title">${article.title}</h3>
            <div class="medium-feed-meta">
              <span class="medium-feed-date">${pubDate}</span>
              <span class="medium-feed-source">${article.source}</span>
            </div>
          </div>
        </div>
      `;
      
      feedGrid.appendChild(article_el);
    });
    
    container.appendChild(feedGrid);
  } catch (error) {
    console.error('Error loading feeds:', error);
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = `<p class="medium-feed-error">Unable to load feeds. Please try again later.</p>`;
    }
  }
}

// Legacy single-feed function for backward compatibility
async function loadMediumFeed(username, containerId, limit = null) {
  loadMultipleFeedsWidget({
    sources: [{ type: 'medium', username, name: 'Medium' }],
    containerId,
    limit
  });
}

function extractImageFromContent(html) {
  if (!html) return null;
  const img = html.match(/<img[^>]+src="([^">]+)"/);
  return img ? img[1] : null;
}

// Auto-initialize if data attribute is present
document.addEventListener('DOMContentLoaded', () => {
  // Handle new multi-source format
  const multiSourceElements = document.querySelectorAll('[data-feed-config]');
  multiSourceElements.forEach(el => {
    const config = JSON.parse(el.dataset.feedConfig);
    loadMultipleFeedsWidget({
      ...config,
      containerId: el.id
    });
  });
  
  // Handle legacy single-source format for backward compatibility
  const feedElements = document.querySelectorAll('[data-medium-feed]');
  feedElements.forEach(el => {
    const username = el.dataset.mediumFeed;
    const limit = parseInt(el.dataset.mediumLimit) || null;
    loadMediumFeed(username, el.id, limit);
  });
});
