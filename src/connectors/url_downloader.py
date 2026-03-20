"""URL downloader for fetching paper exports from remote sources."""
import os
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


class URLDownloader:
    """Downloads paper exports from URLs (GitHub, direct URLs, etc.)."""

    def __init__(
        self,
        timeout: int = 30,
        verify_ssl: bool = True,
        retry_attempts: int = 3,
        cache_dir: Optional[str] = None,
    ):
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.retry_attempts = retry_attempts
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download_file(
        self,
        url: str,
        output_path: Optional[str] = None,
        use_cache: bool = True,
    ) -> tuple[str, str]:
        """Download a file from URL.
        
        Args:
            url: URL to download from
            output_path: Local path to save file (optional)
            use_cache: Whether to use cached version if available
            
        Returns:
            Tuple of (local_path, content)
            
        Raises:
            httpx.HTTPError: If download fails
        """
        cache_key = self._get_cache_key(url)
        
        if use_cache and self.cache_dir:
            cached_path = self.cache_dir / cache_key
            if cached_path.exists():
                logger.info(f"Using cached file: {cached_path}")
                content = cached_path.read_text(encoding="utf-8")
                return str(cached_path), content

        for attempt in range(self.retry_attempts):
            try:
                with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
                    response = client.get(url)
                    response.raise_for_status()
                    content = response.text
                    
                if output_path:
                    path = Path(output_path)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                    logger.info(f"Downloaded: {url} -> {path}")
                    return str(path), content
                
                if self.cache_dir:
                    cached_path = self.cache_dir / cache_key
                    cached_path.write_text(content, encoding="utf-8")
                    return str(cached_path), content
                
                filename = url.split("/")[-1]
                return filename, content
                
            except httpx.HTTPStatusError as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.retry_attempts - 1:
                    raise
            except httpx.RequestError as e:
                logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                if attempt == self.retry_attempts - 1:
                    raise

        raise RuntimeError(f"Failed to download after {self.retry_attempts} attempts")

    def download_multiple(
        self,
        urls: list[str],
        output_dir: str,
        source_name: str,
    ) -> dict[str, dict]:
        """Download multiple files from URLs.
        
        Args:
            urls: List of URLs to download
            output_dir: Directory to save files
            source_name: Name of the source (for logging)
            
        Returns:
            Dict with download results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        results = {
            "successful": [],
            "failed": [],
            "skipped": [],
        }
        
        for url in urls:
            try:
                filename = url.split("/")[-1]
                dest_path = output_path / filename
                
                if dest_path.exists():
                    logger.info(f"File exists, skipping: {dest_path}")
                    results["skipped"].append({
                        "url": url,
                        "path": str(dest_path),
                        "reason": "file_exists",
                    })
                    continue
                
                path, content = self.download_file(url, str(dest_path))
                results["successful"].append({
                    "url": url,
                    "path": path,
                    "size": len(content),
                })
                
            except Exception as e:
                logger.error(f"Failed to download {url}: {e}")
                results["failed"].append({
                    "url": url,
                    "error": str(e),
                })
        
        return results

    def construct_url(self, base_url: str, filename: str) -> str:
        """Construct full URL from base URL and filename."""
        if base_url.endswith("/"):
            return f"{base_url}{filename}"
        return f"{base_url}/{filename}"

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key from URL."""
        import hashlib
        return hashlib.md5(url.encode()).hexdigest() + "_" + url.split("/")[-1]

    def clear_cache(self):
        """Clear the download cache."""
        if self.cache_dir and self.cache_dir.exists():
            for file in self.cache_dir.iterdir():
                file.unlink()
            logger.info(f"Cleared cache: {self.cache_dir}")


def load_data_sources_config(config_path: str = "config/data_sources.yaml") -> dict:
    """Load data sources configuration from YAML."""
    import yaml
    config_file = Path(config_path)
    
    if not config_file.exists():
        logger.warning(f"Config file not found: {config_path}")
        return {}
    
    with open(config_file) as f:
        return yaml.safe_load(f)


def get_source_urls(source_name: str, config: Optional[dict] = None) -> list[str]:
    """Get all URLs for a specific source.
    
    Args:
        source_name: Name of source (wos, ieee, acm, scopus, pubmed)
        config: Optional config dict (loads from file if not provided)
        
    Returns:
        List of URLs to download
    """
    if config is None:
        config = load_data_sources_config()
    
    sources = config.get("sources", {})
    source_config = sources.get(source_name.lower())
    
    if not source_config:
        return []
    
    base_url = source_config.get("base_url", "")
    files = source_config.get("files", [])
    
    urls = []
    for filename in files:
        url = f"{base_url.rstrip('/')}/{filename}" if not base_url.endswith("/") else f"{base_url}{filename}"
        urls.append(url)
    
    return urls


def get_all_source_urls(config: Optional[dict] = None) -> dict[str, list[str]]:
    """Get all URLs for all enabled sources."""
    if config is None:
        config = load_data_sources_config()
    
    sources = config.get("sources", {})
    all_urls = {}
    
    for source_name, source_config in sources.items():
        if source_config.get("enabled", False):
            urls = get_source_urls(source_name, config)
            if urls:
                all_urls[source_name] = urls
    
    return all_urls
