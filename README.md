# lightning-vulns

A list of security advisories for the Lightning Network

> Because in the end it doesn’t matter how feature-rich and easy-to-use the
> Lightning Network is if it can’t keep user funds safe.

― Matt Morehouse, [_DoS: Fake Lightning
Channels_](https://morehouse.github.io/lightning/fake-channel-dos/)

- [LND: HTLC First-Stage Sweep Failure Due to Wallet Budget Constraint](#lnd-htlc-first-stage-sweep-failure-due-to-wallet-budget-constraint)
- [LND: Validation Barrier Map Leak via ChannelAnnouncement Spam](#lnd-validation-barrier-map-leak-via-channelannouncement-spam)
- [LND: Gossip ChannelUpdate Suppression via Validation Barrier Poisoning](#lnd-gossip-channelupdate-suppression-via-validation-barrier-poisoning)
- [LND: Gossip Query Denial of Service](#lnd-gossip-query-denial-of-service)
- [LND: ChannelReestablish Message Queue Out-of-Memory](#lnd-channelreestablish-message-queue-out-of-memory)
- [LND: Gossip Nil-Map Panic on Zero-Timestamp Messages](#lnd-gossip-nil-map-panic-on-zero-timestamp-messages)
- [LND: Infinite Inbox DoS](#lnd-infinite-inbox-dos)
- [LND: Excessive Failback Exploit #2](#lnd-excessive-failback-exploit-2)
- [LND: Replacement Stalling Attack](#lnd-replacement-stalling-attack)
- [Eclair: Preimage Extraction Exploit](#eclair-preimage-extraction-exploit)
- [LND: gossip_timestamp_filter DoS](#lnd-gossip_timestamp_filter-dos)
- [LND: Excessive Failback Exploit](#lnd-excessive-failback-exploit)
- [LDK: Duplicate HTLC Force Close Griefing](#ldk-duplicate-htlc-force-close-griefing)
- [LDK: Invalid Claims Liquidity Griefing](#ldk-invalid-claims-liquidity-griefing)
- [OP_CODESEPARATOR fuzzy match](#op_codeseparator-fuzzy-match)
- [DoS: LND Onion Bomb](#dos-lnd-onion-bomb)
- [DoS: Channel Open Race in CLN](#dos-channel-open-race-in-cln)
- [Invoice Parsing Bugs in CLN](#invoice-parsing-bugs-in-cln)
- [DoS: Fake Lightning Channels](#dos-fake-lightning-channels)
- [Witness Block Parsing DoS Vulnerability](#witness-block-parsing-dos-vulnerability)
- [Erroneous Witness Size Check](#erroneous-witness-size-check)
- [Dust HTLC Exposure](#dust-htlc-exposure)
- [Missing Funding Transaction Output Check](#missing-funding-transaction-output-check)

## LND: HTLC First-Stage Sweep Failure Due to Wallet Budget Constraint

> An anchor-channel peer could prevent a victim lnd node from recovering the
> value of outgoing HTLCs after a force close.
>
> For anchor channels, the first-stage HTLC sweep transaction cannot be funded
> from the HTLC output itself; lnd must contribute internal-wallet inputs to pay
> for the sweep. To guard against fee-estimate uncertainty, lnd required at
> minimum twice the HTLC amount to be available in the internal wallet before
> attempting the sweep. Because lnd’s default configuration holds only the
> anchor reserve (up to 100,000 sats) in the internal wallet, any outgoing HTLC
> above approximately 50,000 sats could go unswept when a channel force-closes —
> the budget check fails and no sweep is attempted.

**Disclosure**: Aug 11, 2026

**Patched**: lnd 0.19.0-beta (May 22, 2025)

**References**:

- https://lightning.community/SI/2026/08/11/lnd-htlc-sweep-budget-failure.html
- https://github.com/lightningnetwork/lnd/pull/9068
- https://github.com/lightningnetwork/lnd/pull/9274
- https://github.com/lightningnetwork/lnd/pull/9627

## LND: Validation Barrier Map Leak via ChannelAnnouncement Spam

> Any peer, with no prior channel relationship, could exhaust a victim lnd
> node’s memory by spamming `channel_announcement` messages. The gossiper’s
> validation barrier initializes internal dependency maps
> (`nodeAnnDependencies`, `chanEdgeDependencies`) for each incoming announcement
> but failed to clean those maps up after processing. An attacker that sends a
> continuous stream of `channel_announcement` messages fills the maps without
> bound, eventually OOM-killing the process.
>
> There is no fund-loss path. The node restarts cleanly once the attacker
> disconnects, but the attack can be repeated.

**Disclosure**: Aug 11, 2026

**Patched**: lnd 0.19.0-beta (May 22, 2025)

**References**:

- https://lightning.community/SI/2026/08/11/lnd-validation-barrier-oom.html

## LND: Gossip ChannelUpdate Suppression via Validation Barrier Poisoning

> Any peer, with no prior channel relationship, could suppress a victim lnd
> node’s processing of `channel_update` or `node_announcement` messages for a
> targeted short channel ID (SCID). The gossiper’s validation barrier gates
> child messages on the successful completion of their parent
> `channel_announcement` validation. An attacker sends many
> `channel_announcement` messages carrying the target SCID but an incorrect
> `chain_hash`; sending each from a different peer bypasses the `recentRejects`
> cache, and every such announcement fails validation. Any legitimate
> `channel_update` for that SCID that arrives while the poisoned announcements
> are in flight is bound to the failing parent and is discarded. Whether a
> specific legitimate update is caught in that window depends on timing, so the
> attack succeeds probabilistically rather than deterministically; the sustained
> spam is also observable as a broader gossip DoS.
>
> The victim will see elevated error-log volume in the gossiper. There is no
> fund-loss path; affected routing-table entries degrade gracefully when stale,
> and routing failures are the worst observable outcome.

**Disclosure**: Aug 11, 2026

**Patched**: lnd 0.19.0-beta (May 22, 2025)

**References**:

- https://lightning.community/SI/2026/08/11/lnd-gossip-update-suppression.html



## LND: Gossip Query Denial of Service

> A peer could render a victim lnd node unresponsive by sending a large volume
> of gossip query messages. Without per-peer connection limits or bytes-based
> rate limiting on gossip query processing, a sustained query stream from a
> single peer could exhaust node resources and cause a denial of service.
>
> There is no fund-loss path. The node restarts cleanly, but the attack can be
> repeated.

**Disclosure**: Aug 11, 2026

**Patched**: lnd 0.19.0-beta (May 22, 2025)

**References**:

- https://lightning.community/SI/2026/08/11/lnd-gossip-queries-dos.html

## LND: ChannelReestablish Message Queue Out-of-Memory

> A peer with pending channels open against a victim lnd node could exhaust the
> node’s heap memory by spamming `channel_reestablish` messages. Each
> connection’s `chanMsgStream` holds up to 1,000 queued messages; pending
> channels do not drain that stream until the link becomes active. A single
> attacker connection could therefore accumulate approximately 20 MB of heap.
> Scaled across the maximum permitted number of pending channels, an attacker
> could force the victim to allocate approximately 20 GB of heap memory,
> OOM-killing the process.
>
> There is no fund-loss path. The node restarts cleanly, but the attack can be
> resumed as long as the pending channel relationships remain.

**Disclosure**: Aug 11, 2026

**Patched**: lnd 0.19.0-beta (May 22, 2025)

**References**:

- https://lightning.community/SI/2026/08/11/lnd-channel-reestablish-oom.html

## LND: Gossip Nil-Map Panic on Zero-Timestamp Messages

> An unauthenticated peer could crash a victim lnd node by sending a
> `channel_update` or `node_announcement` carrying a timestamp of 0. In the
> gossiper’s announcement de-duplication path, a first-seen message with
> timestamp 0 skips both the discard branch and the initialization branch and
> falls through to an assignment into a nil senders map, triggering a panic
> (“assignment to entry in nil map”) that crashes the node.
>
> There is no fund-loss path. The node restarts cleanly, but it can be crashed
> again by repeating the attack.

**Disclosure**: Jun 18, 2026

**Patched**: lnd 0.20.1-beta (Feb 12, 2026)

**References**:

- https://nishantbansal2003.github.io/posts/LND-Zero-Timestamp-Gossip-DoS/
- https://delvingbitcoin.org/t/lnd-zero-timestamp-gossip-dos-disclosure/2621
- https://github.com/lightningnetwork/lnd/pull/10469
- https://lightning.community/SI/2026/06/18/lnd-zero-timestamp-gossip-dos.html

## LND: Infinite Inbox DoS

> Large internal queue sizes and an unrestricted incoming connection policy
> enabled attackers to quickly exhaust LND’s available memory and cause it to
> crash or hang.

**Disclosure**: Dec 4, 2025

**Patched**: lnd 0.19.0

**References**:

- https://delvingbitcoin.org/t/disclosure-critical-vulnerabilities-fixed-in-lnd-0-19-0/2145
- https://morehouse.github.io/lightning/lnd-infinite-inbox-dos/

## LND: Excessive Failback Exploit #2

> A variant of the [previously
> disclosed](https://delvingbitcoin.org/t/disclosure-lnd-excessive-failback-exploit/1493)
> excessive failback bug could still be exploited to steal funds from LND nodes.
> The variant was discovered while drafting an
> [update](https://github.com/lightning/bolts/pull/1233) to BOLT 5 that was
> intended to help prevent similar vulnerabilities in the future.

**Disclosure**: Dec 4, 2025

**Patched**: lnd 0.19.0

**References**:

- https://delvingbitcoin.org/t/disclosure-critical-vulnerabilities-fixed-in-lnd-0-19-0/2145
- https://morehouse.github.io/lightning/lnd-excessive-failback-exploit-2/

## LND: Replacement Stalling Attack

> Weaknesses in LND’s sweeper system enabled an attacker to stall LND’s attempts
> at claiming expired HTLCs on chain. After stalling for 80 blocks, the attacker
> could steal essentially the entire channel balance. This vulnerability was
> discovered during code review of LND’s sweeper rewrite in 2024.

**Disclosure**: Dec 4, 2025

**Patched**: lnd 0.19.0

**References**:

- https://delvingbitcoin.org/t/disclosure-critical-vulnerabilities-fixed-in-lnd-0-19-0/2145
- https://morehouse.github.io/lightning/lnd-replacement-stalling-attack/

## Eclair: Preimage Extraction Exploit

> The vulnerability in Eclair existed in how it monitored the blockchain for
> preimages during a force close. Eclair would only check for HTLCs that existed
> in its local commitment transaction — its own current version of the channel’s
> state. The code incorrectly assumed this local state would always contain a
> complete list of all possible HTLCs.
>
> However, a malicious channel partner could broadcast an older, but still
> valid, commitment transaction. This older state could contain an HTLC that the
> victim’s node had already removed from its own local state. When the attacker
> claimed this HTLC on-chain with a preimage, the victim’s Eclair node would
> ignore it because the HTLC wasn’t in its local records, causing the victim to
> lose the funds.

**Disclosure**: September 23, 2025

**Patched**: eclair 0.12.0

**References**:

- https://morehouse.github.io/lightning/eclair-preimage-extraction-exploit/

## LND: gossip_timestamp_filter DoS

> LND 0.18.2 and below are vulnerable to a denial-of-service (DoS) attack
> involving repeated gossip requests for the full Lightning Network graph. The
> attack is trivial to execute and can cause LND to run out of memory (OOM) and
> crash or hang. You can protect your node by updating to at least LND 0.18.3 or
> by setting `ignore-historical-gossip-filters=true` in your node configuration.

**Disclosure**: July 22, 2025

**Patched**: lnd 0.18.3

**References**:

- https://morehouse.github.io/lightning/lnd-gossip-timestamp-filter-dos/
- https://lightning.community/SI/2026/08/11/lnd-gossip-timestamp-filter-dos.html

## LND: Excessive Failback Exploit

> LND 0.17.5 and below contain a bug in the on-chain resolution logic that can
> be exploited to steal funds. For the attack to be practical the attacker must
> be able to force a restart of the victim node, perhaps via an unpatched DoS
> vector. Update to at least LND 0.18.0 to protect your node.

**Disclosure**: March 4, 2025

**Patched**: lnd 0.18.0

**References**:

- https://morehouse.github.io/lightning/lnd-excessive-failback-exploit/
- https://delvingbitcoin.org/t/disclosure-lnd-excessive-failback-exploit/1493

## LDK: Duplicate HTLC Force Close Griefing

> LDK 0.1 and below are vulnerable to a griefing attack that causes all of the
> victim’s channels to be force closed. Update to LDK 0.1.1 to protect your
> channels.

**Disclosure**: January 29, 2025

**Patched**: ldk 0.1.1

**References**:

- https://morehouse.github.io/lightning/ldk-duplicate-htlc-force-close-griefing/
- https://delvingbitcoin.org/t/disclosure-ldk-duplicate-htlc-force-close-griefing/1410

## LDK: Invalid Claims Liquidity Griefing

> LDK 0.0.125 and below are vulnerable to a liquidity griefing attack against
> anchor channels. The attack locks up funds such that they can only be
> recovered by manually constructing and broadcasting a valid claim transaction.
> Affected users can unlock their funds by upgrading to LDK 0.1 and replaying
> the sequence of commitment and HTLC transactions that led to the lock up.

**Disclosure**: January 23, 2025

**Patched**: ldk 0.1

**References**:

- https://morehouse.github.io/lightning/ldk-invalid-claims-liquidity-griefing/
- https://delvingbitcoin.org/t/disclosure-ldk-invalid-claims-liquidity-griefing/1400

## OP_CODESEPARATOR fuzzy match

[**CVE-2024-38365**](https://www.cve.org/CVERecord?id=CVE-2024-38365) (7.4)

> The btcd Bitcoin client (versions 0.10 to 0.24) did not correctly re-implement
> Bitcoin Core's "FindAndDelete()" functionality. This logic is
> consensus-critical: the difference in behavior with the other Bitcoin clients
> can lead to btcd clients accepting an invalid Bitcoin block (or rejecting a
> valid one).

**Disclosure**: October 10, 2024

**Patched**: btcd v0.24.2

**References**:

- https://delvingbitcoin.org/t/cve-2024-38365-public-disclosure-btcd-findanddelete-bug/1184
- https://github.com/btcsuite/btcd/pull/2178
- https://github.com/btcsuite/btcd/security/advisories/GHSA-27vh-h6mc-q6g8

## DoS: LND Onion Bomb

[**CVE-2024-38359**](https://nvd.nist.gov/vuln/detail/CVE-2024-38359) (6.5)

> A parsing vulnerability in lnd's onion processing logic led to a DoS vector
> due to excessive memory allocation.

**Disclosure**: June 18, 2024

**Patched**: lnd 0.17.0-beta

**References**:

- https://morehouse.github.io/lightning/lnd-onion-bomb/
- https://github.com/lightningnetwork/lnd/security/advisories/GHSA-9gxx-58q6-42p7
- https://delvingbitcoin.org/t/dos-disclosure-lnd-onion-bomb/979
- https://lightning.community/SI/2024/06/20/lnd-onion-bomb.html

## DoS: Channel Open Race in CLN

> CLN versions between 23.02 and 23.05.2 are susceptible to a DoS attack
> involving the exploitation of a race condition during channel opens. If you
> are running any version in this range, your funds may be at risk! Update to at
> least 23.08 to help protect your node.

**Disclosure**: January 8, 2024

**Patched**: cln 23.08

**References**:

- https://morehouse.github.io/lightning/cln-channel-open-race/
- https://delvingbitcoin.org/t/dos-disclosure-channel-open-race-in-cln/385

## Invoice Parsing Bugs in CLN

> Several invoice parsing bugs were fixed in CLN 23.11, including bugs that
> caused crashes, undefined behavior, and use of uninitialized memory. These
> bugs could be reliably triggered by specially crafted invoices, enabling a
> malicious counterparty to crash the victim’s node upon invoice payment.

**Disclosure**: December 8, 2023

**Patched**: cln 23.11

**References**:

- https://morehouse.github.io/lightning/cln-invoice-parsing/

## DoS: Fake Lightning Channels

> Lightning nodes are susceptible to a DoS attack involving the creation of
> large numbers of fake channels.

**Disclosure**: August 23, 2023

**Patched**: lnd 0.16.0, cln 23.02, eclair 0.9.0, ldk 0.0.114

**References**:

- https://morehouse.github.io/lightning/fake-channel-dos/

## Witness Block Parsing DoS Vulnerability

[**CVE-2022-39389**](https://nvd.nist.gov/vuln/detail/CVE-2022-39389) (6.5-8.2)

> All lnd nodes before version v0.15.4 are vulnerable to a block parsing bug
> that can cause a node to enter a degraded state once encountered. In this
> degraded state, nodes can continue to make payments and forward HTLCs, and
> close out channels. Opening channels is prohibited, and also on chain
> transaction events will be undetected.
>
> This can cause loss of funds if a CSV expiry is researched during a breach
> attempt or a CLTV delta expires forgetting the funds in the HTLC.

**Disclosure**: Nov 1, 2022

**Patched**: btcd v0.23.3, lnd v0.15.4-beta

**References**:

- https://github.com/lightningnetwork/lnd/issues/7096
- https://github.com/btcsuite/btcd/issues/1906
- https://github.com/lightningnetwork/lnd/pull/7098
- https://github.com/btcsuite/btcd/pull/1907
- https://github.com/lightningnetwork/lnd/security/advisories/GHSA-hc82-w9v8-83pr
- https://lightning.community/SI/2022/11/17/witness-block-parsing-dos-vulnerability.html
- https://github.com/lightningnetwork/lnd/releases/tag/v0.15.4-beta

## Erroneous Witness Size Check

> A bug would cause nodes to be unable to parse a given block from the wire. The
> block would be properly accepted if fed in via other mechanisms.
>
> The issue here is that the old checks for the maximum witness size, circa
> segwit v0 where placed in the wire package _as well_ as the tx engine. This
> check should only be in the engine, since it's properly gated by other related
> scrip validation flags.
>
> The fix itself is simple: limit witnesses only based on the maximum block size
> in bytes, or ~4MB.

**Disclosure**: Oct 9, 2022

**Patched**: btcd v0.23.2, lnd v0.15.2-beta

**References**:

- https://github.com/lightningnetwork/lnd/issues/7002
- https://github.com/btcsuite/btcd/pull/1896
- https://github.com/lightningnetwork/lnd/pull/7004

## Dust HTLC Exposure

[**CVE-2021-41591**](https://nvd.nist.gov/vuln/detail/CVE-2021-41591) (9.4) |
[**CVE-2021-41592**](https://nvd.nist.gov/vuln/detail/CVE-2021-41592) (9.4) |
[**CVE-2021-41593**](https://nvd.nist.gov/vuln/detail/CVE-2021-41593) (8.6)

> The current BOLT specification only requires Alice's `dust_limit_satoshis`
> (applied on Alice's commitment) to be under Alice's `channel_reserve_satoshis`
> (applied on Bob). As those 2 parameters are selectable by Alice, she can
> inflate the dust limit until reaching the implementation-defined max value.

**Disclosure**: Oct 4, 2021

**Patched**: eclair v0.6.2, lnd v0.13.3, ldk v0.0.102

**References**:

- https://diyhpl.us/~bryan/irc/bitcoin/bitcoin-dev/linuxfoundation-pipermail/lightning-dev/2021-October/003257.txt

## Missing Funding Transaction Output Check

[**CVE-2019-12998**](https://nvd.nist.gov/vuln/detail/CVE-2019-12998) (7.5) |
[**CVE-2019-12999**](https://nvd.nist.gov/vuln/detail/CVE-2019-12999) (7.5) |
[**CVE-2019-13000**](https://nvd.nist.gov/vuln/detail/CVE-2019-13000) (7.5)

> A lightning node accepting a channel must check that the funding transaction
> output does indeed open the channel proposed. Otherwise an attacker can claim
> to open a channel but either not pay to the peer, or not pay the full amount.
> Once that transaction reaches the minimum depth, it can spend funds from the
> channel. The victim will only notice when it tries to close the channel and
> none of the commitment or mutual close transactions it has are valid.

**Disclosure**: September 27, 2019

**Patched**: c-lightning v0.7.1, lnd v0.7.1, eclair v0.3.1

**References**:

- https://lists.linuxfoundation.org/pipermail/lightning-dev/2019-September/002174.html
