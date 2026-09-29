# Analytics methodology and example results

## Overall lineup performance

Offensive rating is points scored per 100 offensive possessions. Defensive rating is points allowed per 100 defensive possessions. Net rating is the difference between the two.

Recommendations require at least one possession on each end. A missing defensive sample is not evidence that a lineup allowed zero points. The dashboard shows one selected lineup per category; equal net ratings are not a claim of a unique winner.

In the fixture data, nine eligible lineups tie at +200.0 net rating. Examples include:

- The Avengers: Falcon, Scarlet Witch, Wolverine, Black Widow, and Groot.
- Tune Squad: Foghorn Leghorn, Wile E. Coyote, Daffy Duck, LeBron James, and Speedy Gonzales.

## On-court player performance

Wasp has the highest on-court net rating in the fixture data: +54.5, from a 154.5 offensive rating and a 100.0 defensive rating. This describes team performance while the player is on the court; it does not isolate a causal individual contribution or adjust for teammates and opponents.

## Rebounding recommendations

The rebounding recommendation ranks the sum of offensive and defensive rebound percentages, then uses net rating to break ties. For The Avengers, this selects Hawkeye, Dr. Strange, Wong, Captain Marvel, and Thor: 100% offensive rebounding, 100% defensive rebounding, and +100.0 net rating in the observed possessions.

Defensive rebounding limits opponents' second-chance opportunities, while offensive rebounding extends the team's own scoring opportunities. This makes the group a useful example against a hypothetical opponent that emphasizes rebounding, rather than proof of performance against that opponent.

## Interpretation limits

The data is intentionally small. Extreme ratings and 100% rebound rates can result from very few opportunities, and the recommendations do not apply a minimum sample threshold beyond requiring both offensive and defensive possessions. Review possession and opportunity counts alongside rates.
