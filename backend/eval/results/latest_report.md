# DataPilot Eval Report
**Date**: 2026-03-12T19:02

## Summary
| Metric | Value |
|--------|-------|
| Execution Success Rate | **95.0%** (19/20) |
| Result Match Rate | **50.0%** (10/20) |
| Avg Latency | 23633 ms |

## By Difficulty
| Difficulty | Match Rate |
|------------|------------|
| easy | 4/6 (67%) |
| hard | 2/4 (50%) |
| medium | 4/10 (40%) |

## By Category
| Category | Match Rate |
|----------|------------|
| bookings | 3/7 (43%) |
| cancellations | 1/2 (50%) |
| properties | 3/4 (75%) |
| revenue | 3/7 (43%) |

## Per-Query Results
| ID | Difficulty | Category | Success | Match | GEval | Latency |
|----|-----------|----------|---------|-------|-------|---------|
| q001 | easy | revenue | [OK] | [FAIL] | — | 24378ms |
| q002 | medium | revenue | [OK] | [FAIL] | — | 26735ms |
| q003 | easy | bookings | [OK] | [OK] | — | 23704ms |
| q004 | medium | bookings | [OK] | [FAIL] | — | 21073ms |
| q005 | medium | bookings | [OK] | [FAIL] | — | 10489ms |
| q006 | medium | revenue | [OK] | [FAIL] | — | 42447ms |
| q007 | easy | properties | [OK] | [OK] | — | 19466ms |
| q008 | medium | properties | [OK] | [OK] | — | 27902ms |
| q009 | easy | cancellations | [OK] | [OK] | — | 25253ms |
| q010 | hard | bookings | [OK] | [FAIL] | — | 25437ms |
| q011 | medium | revenue | [OK] | [OK] | — | 23596ms |
| q012 | easy | properties | [OK] | [OK] | — | 16401ms |
| q013 | hard | revenue | [OK] | [OK] | — | 42156ms |
| q014 | medium | bookings | [OK] | [OK] | — | 18773ms |
| q015 | medium | cancellations | [OK] | [FAIL] | — | 23470ms |
| q016 | hard | revenue | [FAIL] | — | — | 0ms |
| q017 | easy | bookings | [OK] | [FAIL] | — | 26461ms |
| q018 | medium | properties | [OK] | [FAIL] | — | 22126ms |
| q019 | medium | revenue | [OK] | [OK] | — | 22265ms |
| q020 | hard | bookings | [OK] | [OK] | — | 30530ms |