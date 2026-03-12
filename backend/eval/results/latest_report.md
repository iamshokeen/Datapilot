# DataPilot Eval Report
**Date**: 2026-03-12T19:25

## Summary
| Metric | Value |
|--------|-------|
| Execution Success Rate | **100.0%** (20/20) |
| Result Match Rate | **55.0%** (11/20) |
| Avg GEval Score | **0.859** / 1.000 |
| Avg Latency | 24559 ms |

## By Difficulty
| Difficulty | Match Rate |
|------------|------------|
| easy | 5/6 (83%) |
| hard | 2/4 (50%) |
| medium | 4/10 (40%) |

## By Category
| Category | Match Rate |
|----------|------------|
| bookings | 3/7 (43%) |
| cancellations | 1/2 (50%) |
| properties | 3/4 (75%) |
| revenue | 4/7 (57%) |

## Per-Query Results
| ID | Difficulty | Category | Success | Match | GEval | Latency |
|----|-----------|----------|---------|-------|-------|---------|
| q001 | easy | revenue | [OK] | [OK] | 0.86 | 23635ms |
| q002 | medium | revenue | [OK] | [FAIL] | 0.89 | 23862ms |
| q003 | easy | bookings | [OK] | [OK] | 0.90 | 21825ms |
| q004 | medium | bookings | [OK] | [FAIL] | 0.92 | 19394ms |
| q005 | medium | bookings | [OK] | [FAIL] | 0.40 | 10284ms |
| q006 | medium | revenue | [OK] | [FAIL] | 0.88 | 50567ms |
| q007 | easy | properties | [OK] | [OK] | 0.89 | 19418ms |
| q008 | medium | properties | [OK] | [OK] | 0.88 | 24231ms |
| q009 | easy | cancellations | [OK] | [OK] | 0.90 | 20972ms |
| q010 | hard | bookings | [OK] | [FAIL] | 0.84 | 26671ms |
| q011 | medium | revenue | [OK] | [OK] | 0.92 | 19981ms |
| q012 | easy | properties | [OK] | [OK] | 0.91 | 17551ms |
| q013 | hard | revenue | [OK] | [OK] | 0.79 | 30785ms |
| q014 | medium | bookings | [OK] | [OK] | 0.93 | 25612ms |
| q015 | medium | cancellations | [OK] | [FAIL] | 0.77 | 22936ms |
| q016 | hard | revenue | [OK] | [FAIL] | 0.91 | 36997ms |
| q017 | easy | bookings | [OK] | [FAIL] | 0.84 | 21706ms |
| q018 | medium | properties | [OK] | [FAIL] | 0.92 | 26302ms |
| q019 | medium | revenue | [OK] | [OK] | 0.91 | 21098ms |
| q020 | hard | bookings | [OK] | [OK] | 0.93 | 27362ms |