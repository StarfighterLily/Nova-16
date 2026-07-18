"""
Instruction Cache Benchmark Tests

Tests LRU vs FIFO cache performance by exercising non-sequential fetches
(jumps, calls, interrupt handlers) that benefit from LRU's smarter eviction.
"""

import pytest
import time
from nova.memory import Memory
from nova.bus import EventBus


class TestInstructionCache:
    """Test instruction cache behavior and performance."""

    def test_cache_full_clear_eviction(self):
        """Verify clear-on-full eviction: a hit on a full cache keeps all
        entries (no per-access reordering cost), and a miss on a full cache
        clears the whole cache before inserting the new entry.

        This replaced strict LRU eviction after benchmarking showed
        OrderedDict.move_to_end() on every cache hit cost more than the
        occasional full-clear it was traded for — real branch-target working
        sets (loop back-edges) are small and stable, so full clears are rare
        in practice. See nova/memory/memory.py fetch_opcode().
        """
        mem = Memory()

        # Fill cache to capacity
        for addr in range(0x1000, 0x1000 + mem.ICACHE_SIZE):
            mem._icache[addr] = 0x90 + (addr & 0x0F)  # NOP-like opcodes

        # A hit on a full cache must not evict or reorder anything.
        _ = mem.fetch_opcode(0x1000)
        assert len(mem._icache) == mem.ICACHE_SIZE
        assert 0x1001 in mem._icache, "hit on a full cache must not evict other entries"

        # A miss on a full cache clears the whole cache, then inserts the new entry.
        mem.fetch_opcode(0x2000)
        assert len(mem._icache) == 1
        assert 0x2000 in mem._icache
        assert 0x1000 not in mem._icache, "miss on a full cache must clear stale entries"

    def test_cache_statistics(self):
        """Verify cache hit/miss statistics are tracked correctly."""
        mem = Memory()
        
        # Reset statistics by clearing cache
        mem._icache_hits = 0
        mem._icache_misses = 0
        
        # First fetch - miss
        mem._last_fetch_pc = None  # Force non-sequential
        _ = mem.fetch_opcode(0x1000)
        assert mem._icache_misses == 1
        assert mem._icache_hits == 0
        
        # Second fetch same address - hit
        _ = mem.fetch_opcode(0x1000)
        assert mem._icache_hits == 1
        assert mem._icache_misses == 1
        
        # Statistics method
        stats = mem.get_cache_stats()
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 1
        assert stats['cache_hit_rate'] == 0.5

    def test_sequential_bypass(self):
        """Verify sequential fetches bypass cache entirely."""
        mem = Memory()
        
        # Sequential fetch should increment sequential counter, not cache stats
        mem._icache_hits = 0
        mem._icache_misses = 0
        mem._sequential_count = 0
        
        # First fetch (non-sequential since _last_fetch_pc is None)
        _ = mem.fetch_opcode(0x1000)
        assert mem._icache_misses == 1
        assert mem._icache_hits == 0
        
        # Second sequential fetch - should bypass cache
        _ = mem.fetch_opcode(0x1001)
        assert mem._sequential_count == 1, "Second sequential should be counted"
        assert mem._icache_misses == 1, "Sequential should not count as miss"
        assert mem._icache_hits == 0
        
        # Third sequential fetch
        _ = mem.fetch_opcode(0x1002)
        assert mem._sequential_count == 2
        assert mem._icache_misses == 1  # Still just 1 miss (initial)

    def test_cache_invalidation_on_write(self):
        """Verify cache entries are invalidated when memory is written."""
        mem = Memory()
        
        # Prime the cache
        mem.fetch_opcode(0x1000)
        assert 0x1000 in mem._icache
        
        # Write to the cached address
        mem.write_byte(0x1000, 0xFF)
        
        # Entry should be removed
        assert 0x1000 not in mem._icache


class TestInstructionCachePerformance:
    """Performance benchmarks comparing LRU vs theoretical FIFO."""

    def test_lru_loop_performance(self):
        """
        Test that LRU keeps frequently-jumped-to addresses cached.
        
        Simulates a program that calls/jumps to a small set of addresses
        repeatedly, which should benefit from LRU keeping hot entries cached.
        """
        mem = Memory()
        mem._icache_hits = 0
        mem._icache_misses = 0
        
        # Simulate a loop that jumps between 8 hot addresses
        # This pattern should keep those addresses cached with LRU
        hot_addresses = [0x2000, 0x2010, 0x2020, 0x2030, 
                        0x2040, 0x2050, 0x2060, 0x2070]
        
        # First, fill the cache with cold entries
        for addr in range(0x3000, 0x3000 + mem.ICACHE_SIZE):
            mem.fetch_opcode(addr)
        
        # Now do many fetches to hot addresses (with jumps)
        # The cache is full, so without LRU, we'd get poor hit rate
        initial_misses = mem._icache_misses
        
        # Do 100 iterations of the hot loop
        for _ in range(100):
            for addr in hot_addresses:
                mem.fetch_opcode(addr)
        
        # With LRU, we should have good hit rate since hot addresses are reused
        # With FIFO, we'd have many misses since hot addresses would be evicted
        # Calculate hit rate for just the hot loop (excluding cold fill)
        loop_hits = mem._icache_hits
        loop_misses = mem._icache_misses - initial_misses
        loop_total = loop_hits + loop_misses
        hit_rate = loop_hits / loop_total if loop_total > 0 else 0
        
        # LRU should give us > 90% hit rate for this pattern
        assert hit_rate > 0.9, \
            f"LRU hit rate too low: {hit_rate:.2%} (hits={loop_hits}, misses={loop_misses})"


@pytest.mark.slow
class TestInstructionCacheBenchmark:
    """Detailed performance benchmarks (may be slow)."""

    def test_large_scale_lru_performance(self):
        """Large-scale test of LRU cache performance with mixed access patterns."""
        mem = Memory()
        mem._icache_hits = 0
        mem._icache_misses = 0
        
        # Mix of sequential (bypassed) and random accesses
        # This simulates real program behavior
        hot_addresses = [0x1000 + i * 16 for i in range(16)]
        cold_addresses = [0x5000 + i for i in range(0, 1000, 16)]
        
        # Fill cache with cold addresses first
        for addr in cold_addresses[:mem.ICACHE_SIZE]:
            mem.fetch_opcode(addr)
        
        # Now interleave hot and cold accesses
        for _ in range(500):
            # Random cold access (with jumps)
            addr = (0x5000 + (_ * 7) % 1000)
            mem.fetch_opcode(addr)
            
            # Hot access (should benefit from LRU)
            hot_addr = hot_addresses[(_ * 3) % 16]
            mem.fetch_opcode(hot_addr)
        
        # Report results
        total = mem._icache_hits + mem._icache_misses
        hit_rate = mem._icache_hits / total if total > 0 else 0
        
        print(f"\nLRU Cache Performance:")
        print(f"  Total cache accesses: {total}")
        print(f"  Cache hits: {mem._icache_hits}")
        print(f"  Cache misses: {mem._icache_misses}")
        print(f"  Hit rate: {hit_rate:.2%}")


def test_lru_vs_fifo_analysis():
    """
    Analyze why LRU is better than FIFO for instruction cache.
    
    This test demonstrates the theoretical advantage:
    - FIFO: evicts in insertion order, ignoring reuse patterns
    - LRU: keeps frequently-reused addresses cached longer
    """
    # Key insight: With sequential fetch bypass, FIFO already has low thrashing
    # LRU adds value for:
    # 1. Jump tables (same addresses hit repeatedly)
    # 2. Repeated function calls (return addresses)
    # 3. Interrupt handlers (same vector addresses)
    
    # The sequential optimization handles the "stream of sequential addresses" case
    # LRU handles the "small hot set" case
    
    print("\nInstruction Cache Analysis:")
    print(f"  Current cache: {Memory.ICACHE_SIZE} entries")
    print("  Sequential bypass: Already implemented (avoids thrashing)")
    print("  LRU benefit: Non-sequential hot addresses stay cached")
    print("  Overhead: move_to_end() is O(1) in OrderedDict")


if __name__ == "__main__":
    # Run quick tests
    test_lru_vs_fifo_analysis()
    
    # Run pytest
    pytest.main([__file__, "-v", "-s"])