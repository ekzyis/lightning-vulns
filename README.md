# lightning-vulns

A list of lightning CVEs (Common Vulnerabilities and Exposures).

## LND: Infinite Inbox DoS

> Large internal queue sizes and an unrestricted incoming connection policy enabled attackers to quickly exhaust LND’s available memory and cause it to crash or hang.

**Disclosure**: Dec 4, 2025

**Patched**: lnd 0.19.0

**References**:

- https://delvingbitcoin.org/t/disclosure-critical-vulnerabilities-fixed-in-lnd-0-19-0/2145
- https://morehouse.github.io/lightning/lnd-infinite-inbox-dos/

## LND: Excessive Failback Exploit #2

> A variant of the [previously disclosed](https://delvingbitcoin.org/t/disclosure-lnd-excessive-failback-exploit/1493) excessive failback bug could still be exploited to steal funds from LND nodes. The variant was discovered while drafting an [update](https://github.com/lightning/bolts/pull/1233) to BOLT 5 that was intended to help prevent similar vulnerabilities in the future.

**Disclosure**: Dec 4, 2025

**Patched**: lnd 0.19.0

**References**:

- https://delvingbitcoin.org/t/disclosure-critical-vulnerabilities-fixed-in-lnd-0-19-0/2145
- https://morehouse.github.io/lightning/lnd-excessive-failback-exploit-2/

## LND: Replacement Stalling Attack

> Weaknesses in LND’s sweeper system enabled an attacker to stall LND’s attempts at claiming expired HTLCs on chain. After stalling for 80 blocks, the attacker could steal essentially the entire channel balance. This vulnerability was discovered during code review of LND’s sweeper rewrite in 2024.

**Disclosure**: Dec 4, 2025

**Patched**: lnd 0.19.0

**References**:

- https://delvingbitcoin.org/t/disclosure-critical-vulnerabilities-fixed-in-lnd-0-19-0/2145
- https://morehouse.github.io/lightning/lnd-replacement-stalling-attack/

## Eclair: Preimage Extraction Exploit

> The vulnerability in Eclair existed in how it monitored the blockchain for preimages during a force close. Eclair would only check for HTLCs that existed in its local commitment transaction — its own current version of the channel’s state. The code incorrectly assumed this local state would always contain a complete list of all possible HTLCs.
>
> However, a malicious channel partner could broadcast an older, but still valid, commitment transaction. This older state could contain an HTLC that the victim’s node had already removed from its own local state. When the attacker claimed this HTLC on-chain with a preimage, the victim’s Eclair node would ignore it because the HTLC wasn’t in its local records, causing the victim to lose the funds.

**Disclosure**: September 23, 2025

**Patched**: eclair 0.12.0

**References**:

- https://morehouse.github.io/lightning/eclair-preimage-extraction-exploit/

## DoS: LND Onion Bomb

[**CVE-2024-38359**](https://nvd.nist.gov/vuln/detail/CVE-2024-38359) (6.5)

> A parsing vulnerability in lnd's onion processing logic led to a DoS vector due to excessive memory allocation.

**Disclosure**: June 18, 2024

**Patched**: lnd 0.17.0-beta

**References**:

- https://morehouse.github.io/lightning/lnd-onion-bomb/
- https://github.com/lightningnetwork/lnd/security/advisories/GHSA-9gxx-58q6-42p7
- https://delvingbitcoin.org/t/dos-disclosure-lnd-onion-bomb/979

## btcd Block Parsing Bug

[**CVE-2022-39389**](https://nvd.nist.gov/vuln/detail/CVE-2022-39389) (6.5-8.2)

> All lnd nodes before version v0.15.4 are vulnerable to a block parsing bug that can cause a node to enter a degraded state once encountered. In this degraded state, nodes can continue to make payments and forward HTLCs, and close out channels. Opening channels is prohibited, and also on chain transaction events will be undetected. This can cause loss of funds if a CSV expiry is researched during a breach attempt or a CLTV delta expires forgetting the funds in the HTLC.

**Disclosure**: Nov 1, 2022

**Patched**: lnd v0.23.3, lnd v0.15.4-beta

**References**:

- https://github.com/lightningnetwork/lnd/issues/7096
- https://github.com/lightningnetwork/lnd/pull/7098
- https://github.com/lightningnetwork/lnd/security/advisories/GHSA-hc82-w9v8-83pr

## Dust HTLC Exposure

[**CVE-2021-41591**](https://nvd.nist.gov/vuln/detail/CVE-2021-41591) (9.4) | [**CVE-2021-41592**](https://nvd.nist.gov/vuln/detail/CVE-2021-41592) (9.4) | [**CVE-2021-41593**](https://nvd.nist.gov/vuln/detail/CVE-2021-41593) (8.6)

> The current BOLT specification only requires Alice's `dust_limit_satoshis` (applied on Alice's commitment) to be under Alice's `channel_reserve_satoshis` (applied on Bob). As those 2 parameters are selectable by Alice, she can inflate the dust limit until reaching the implementation-defined max value.

**Disclosure**: Oct 4, 2021

**Patched**: eclair v0.6.2, lnd v0.13.3, ldk v0.0.102

**References**:

- https://diyhpl.us/~bryan/irc/bitcoin/bitcoin-dev/linuxfoundation-pipermail/lightning-dev/2021-October/003257.txt

## Missing Funding Transaction Output Check

[**CVE-2019-12998**](https://nvd.nist.gov/vuln/detail/CVE-2019-12998) (7.5) | [**CVE-2019-12999**](https://nvd.nist.gov/vuln/detail/CVE-2019-12999) (7.5) | [**CVE-2019-13000**](https://nvd.nist.gov/vuln/detail/CVE-2019-13000) (7.5)

> A lightning node accepting a channel must check that the funding transaction output does indeed open the channel proposed. Otherwise an attacker can claim to open a channel but either not pay to the peer, or not pay the full amount. Once that transaction reaches the minimum depth, it can spend funds from the channel. The victim will only notice when it tries to close the channel and none of the commitment or mutual close transactions it has are valid. 

**Disclosure**: September 27, 2019

**Patched**: c-lightning v0.7.1, lnd v0.7.1, eclair v0.3.1

**References**:

- https://lists.linuxfoundation.org/pipermail/lightning-dev/2019-September/002174.html
