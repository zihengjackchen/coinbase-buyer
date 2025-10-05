# Enhanced DCA

## Goal

Automate a price-aware DCA that:

* Buys **more** when the market is cheap,
* Buys **less** when the market is hot,
* Keeps **dry powder** for real dips,
* Uses **guardrails** to avoid overexposure.

## Signals & Windows

* **Short window**: recent average (captures quick dips/rallies).
* **Medium window**: trend average (stability filter).
* **Long window**: recent-history percentiles (what’s “cheap” vs “expensive”).

## Multipliers (qualitative)

1. **Dynamic (short vs. medium)**

   * Increases when price is below both short & medium averages, decreases when above both.
   * If signals conflict (below one but above the other), the effect softens toward neutral.

2. **Window (percentiles)**

   * If price sits in the “cheap zone” of the long window, boost a bit.
   * If price sits in the “expensive zone,” cut a bit.
   * Neutral in the middle.

3. **Reserve**

   * In normal times, hold back a small portion of baseline buys.
   * On **deep dip** vs the medium trend, release the reserve and add a small kicker.

> The three multipliers **stack** (then get clipped to a safe band).

## Decision Flow

1. **Safety check (optional)**

   * If price is above a hard ceiling and above short average → **skip**.
2. **Compute multipliers**

   * **Dynamic** (short vs medium)
   * **Window** (long-window cheap/expensive)
   * **Reserve** (holdback vs release on deep dip)
3. **Combine & clip**

   * Multiply the three effects, then clip within a min/max band to avoid extremes.
4. **Spend sizing**

   * Effective buy = baseline × combined multiplier
   * Enforce per-run cap and minimum order size.
5. **Place post-only limit**

   * Slightly below current price to improve fill quality (or skip if safety dictates).

## Why Each Part Exists

* **Short window**: fast reaction to fresh dips/rallies.
* **Medium window**: prevents overreacting to noise.
* **Long window percentiles**: gives cycle context (“cheap vs expensive” recently).
* **Reserve**: ensures firepower in real drawdowns.
* **Guardrails**: prevents overspending or dust orders.

## Tuning Knobs (conceptual)

* **Short/Medium horizon**: shorter → more responsive; longer → more stable.
* **Sensitivity**: how quickly the dynamic multiplier grows/shrinks as price moves.
* **Window bands**: how generous the “cheap/expensive” zones are.
* **Reserve fraction**: how much you hold back in normal times.
* **Deep-dip threshold**: how far below the medium trend to release reserves.
* **Boost/Cut sizes**: mild nudges vs aggressive shifts.
* **Min/Max multipliers**: global guardrails.
* **Per-run spend cap / min order**: practical constraints for fees and risk.

## Example Behaviors (qualitative)

* **Shallow dip**: dynamic says “slightly more,” window neutral, reserve held → buy ≈ baseline.
* **Deep dip**: dynamic strong, window cheap, reserve released → buy > baseline.
* **Rally**: dynamic down, window expensive, reserve held → buy < baseline.
* **Mixed signals**: dynamic softens to neutral until short/medium agree.

## Observability

Each run logs:

* Current price, short/medium snapshots, long-window bands,
* Individual multipliers, combined multiplier, and final spend,
* Skip reasons (if any) to make tuning easy.