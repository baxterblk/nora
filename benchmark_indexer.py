#!/usr/bin/env python3
"""
Benchmark script for ProjectIndexer caching performance.

Tests indexing performance with and without caching on the NORA codebase.
"""

import time
from nora.core.indexer import ProjectIndexer


def benchmark_indexing():
    """Benchmark ProjectIndexer performance."""
    indexer = ProjectIndexer()
    project_path = "."

    # Benchmark 1: Full index (no cache)
    print("=" * 60)
    print("Benchmark 1: Full indexing (no cache)")
    print("=" * 60)
    start = time.time()
    index_data_no_cache = indexer.index_project(project_path, project_name="nora", use_cache=False)
    duration_no_cache = time.time() - start

    print(f"Duration: {duration_no_cache:.2f}s")
    print(f"Files indexed: {index_data_no_cache['total_files']}")
    print(f"Total size: {index_data_no_cache['total_size']:,} bytes")
    print(f"Languages: {index_data_no_cache['languages']}")
    print()

    # Save index for caching test
    indexer.save_index(index_data_no_cache)

    # Benchmark 2: Re-index with cache (no files changed)
    print("=" * 60)
    print("Benchmark 2: Re-indexing with cache (no changes)")
    print("=" * 60)
    start = time.time()
    index_data_cached = indexer.index_project(project_path, project_name="nora", use_cache=True)
    duration_cached = time.time() - start

    print(f"Duration: {duration_cached:.2f}s")
    print(f"Files indexed: {index_data_cached['total_files']}")
    print(f"Total size: {index_data_cached['total_size']:,} bytes")
    print()

    # Calculate improvement
    speedup = duration_no_cache / duration_cached
    time_saved = duration_no_cache - duration_cached
    percent_saved = (time_saved / duration_no_cache) * 100

    print("=" * 60)
    print("Performance Results")
    print("=" * 60)
    print(f"Without cache: {duration_no_cache:.2f}s")
    print(f"With cache:    {duration_cached:.2f}s")
    print(f"Speedup:       {speedup:.1f}x faster")
    print(f"Time saved:    {time_saved:.2f}s ({percent_saved:.0f}%)")
    print()

    # Calculate cache hit rate
    total_files = index_data_cached['total_files']
    # This would need logging output to calculate accurately
    print("Note: Cache hit rate is logged during indexing")
    print("      Check logs for: 'Cache hits: X/Y files (Z%)'")
    print()


if __name__ == "__main__":
    benchmark_indexing()
