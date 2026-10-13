"""GraphQL documents for the Mina daemon API.

These are the documents of ``spec/operations.graphql``, the common API of the
Mina SDKs (see ``spec/SPEC.md``). ``spec/`` is a copy of o1-labs/mina-sdk-spec
at the tag in ``spec/VERSION``; ``tests/test_spec.py`` checks that these
documents stay identical. Change the specification first.
"""

SYNC_STATUS = """query SyncStatus {
  syncStatus
}"""

DAEMON_STATUS = """query DaemonStatus {
  daemonStatus {
    syncStatus
    blockchainLength
    highestBlockLengthReceived
    highestUnvalidatedBlockLengthReceived
    uptimeSecs
    stateHash
    commitId
    numAccounts
    ledgerMerkleRoot
    chainId
    catchupStatus
    blockProductionKeys
    coinbaseReceiver
    globalSlotSinceGenesisBestTip
    consensusTimeNow {
      epoch
      slot
      globalSlot
      startTime
      endTime
    }
    peers {
      peerId
      host
      libp2pPort
    }
    addrsAndPorts {
      externalIp
      bindIp
      clientPort
      libp2pPort
      peer {
        host
        libp2pPort
        peerId
      }
    }
  }
}"""

DAEMON_METRICS = """query DaemonMetrics {
  daemonStatus {
    metrics {
      blockProductionDelay
      transactionPoolDiffReceived
      transactionPoolDiffBroadcasted
      transactionsAddedToPool
      transactionPoolSize
      snarkPoolDiffReceived
      snarkPoolDiffBroadcasted
      pendingSnarkWork
      snarkPoolSize
    }
  }
}"""

NETWORK_ID = """query NetworkId {
  networkID
}"""

GET_ACCOUNT = """query Account($publicKey: PublicKey!, $token: TokenId) {
  account(publicKey: $publicKey, token: $token) {
    publicKey
    nonce
    delegate
    tokenId
    tokenSymbol
    votingFor
    receiptChainHash
    balance {
      total
      liquid
      locked
      blockHeight
    }
    timing {
      initialMinimumBalance
      cliffTime
      cliffAmount
      vestingPeriod
      vestingIncrement
    }
    permissions {
      editState
      send
      receive
      access
      setDelegate
      setPermissions
      setVerificationKey {
        auth
        txnVersion
      }
      setZkappUri
      editActionState
      setTokenSymbol
      incrementNonce
      setVotingFor
      setTiming
    }
    zkappState
    provedState
    zkappUri
  }
}"""

BEST_CHAIN = """query BestChain($maxLength: Int) {
  bestChain(maxLength: $maxLength) {
    stateHash
    commandTransactionCount
    creatorAccount {
      publicKey
    }
    protocolState {
      previousStateHash
      consensusState {
        blockHeight
        epoch
        slot
        slotSinceGenesis
        blockCreator
        coinbaseReceiever
        stakingEpochData {
          epochLength
          seed
          ledger {
            hash
          }
        }
        nextEpochData {
          seed
          ledger {
            hash
          }
        }
      }
      blockchainState {
        date
        utcDate
        snarkedLedgerHash
        stagedLedgerHash
      }
    }
    snarkJobs {
      prover
      fee
      workIds
    }
    transactions {
      coinbase
      coinbaseReceiverAccount {
        publicKey
      }
      feeTransfer {
        recipient
        fee
        type
      }
      userCommands {
        id
        hash
        kind
        nonce
        source {
          publicKey
        }
        receiver {
          publicKey
        }
        amount
        fee
        memo
        failureReason
      }
      zkappCommands {
        id
        hash
        failureReason {
          index
          failures
        }
        zkappCommand {
          memo
          feePayer {
            authorization
            body {
              publicKey
              fee
              nonce
              validUntil
            }
          }
          accountUpdates {
            authorization {
              signature
              proof
            }
            body {
              publicKey
              tokenId
              callDepth
              callData
              actions
              events
              incrementNonce
              useFullCommitment
              implicitAccountCreationFee
              balanceChange {
                magnitude
                sgn
              }
              mayUseToken {
                parentsOwnToken
                inheritFromParent
              }
              authorizationKind {
                isSigned
                isProved
                verificationKeyHash
              }
              update {
                appState
                delegate
                zkappUri
                votingFor
                tokenSymbol
                verificationKey {
                  hash
                  data
                }
                timing {
                  initialMinimumBalance
                  cliffTime
                  cliffAmount
                  vestingPeriod
                  vestingIncrement
                }
                permissions {
                  editState
                  send
                  receive
                  access
                  setDelegate
                  setPermissions
                  setVerificationKey {
                    auth
                    txnVersion
                  }
                  setZkappUri
                  editActionState
                  setTokenSymbol
                  incrementNonce
                  setVotingFor
                  setTiming
                }
              }
              preconditions {
                validWhile {
                  lower
                  upper
                }
                network {
                  snarkedLedgerHash
                  blockchainLength {
                    lower
                    upper
                  }
                  minWindowDensity {
                    lower
                    upper
                  }
                  totalCurrency {
                    lower
                    upper
                  }
                  globalSlotSinceGenesis {
                    lower
                    upper
                  }
                  stakingEpochData {
                    seed
                    startCheckpoint
                    lockCheckpoint
                    epochLength {
                      lower
                      upper
                    }
                    ledger {
                      hash
                      totalCurrency {
                        lower
                        upper
                      }
                    }
                  }
                  nextEpochData {
                    seed
                    startCheckpoint
                    lockCheckpoint
                    epochLength {
                      lower
                      upper
                    }
                    ledger {
                      hash
                      totalCurrency {
                        lower
                        upper
                      }
                    }
                  }
                }
                account {
                  balance {
                    lower
                    upper
                  }
                  nonce {
                    lower
                    upper
                  }
                  receiptChainHash
                  delegate
                  state
                  actionState
                  provedState
                  isNew
                }
              }
            }
          }
        }
      }
    }
  }
}"""

GENESIS_BLOCK = """query GenesisBlock {
  genesisBlock {
    stateHash
    commandTransactionCount
    creatorAccount {
      publicKey
    }
    protocolState {
      previousStateHash
      consensusState {
        blockHeight
        epoch
        slot
        slotSinceGenesis
        blockCreator
        coinbaseReceiever
        stakingEpochData {
          epochLength
          seed
          ledger {
            hash
          }
        }
        nextEpochData {
          seed
          ledger {
            hash
          }
        }
      }
      blockchainState {
        date
        utcDate
        snarkedLedgerHash
        stagedLedgerHash
      }
    }
    snarkJobs {
      prover
      fee
      workIds
    }
    transactions {
      coinbase
      coinbaseReceiverAccount {
        publicKey
      }
      feeTransfer {
        recipient
        fee
        type
      }
      userCommands {
        id
        hash
        kind
        nonce
        source {
          publicKey
        }
        receiver {
          publicKey
        }
        amount
        fee
        memo
        failureReason
      }
      zkappCommands {
        id
        hash
        failureReason {
          index
          failures
        }
        zkappCommand {
          memo
          feePayer {
            authorization
            body {
              publicKey
              fee
              nonce
              validUntil
            }
          }
          accountUpdates {
            authorization {
              signature
              proof
            }
            body {
              publicKey
              tokenId
              callDepth
              callData
              actions
              events
              incrementNonce
              useFullCommitment
              implicitAccountCreationFee
              balanceChange {
                magnitude
                sgn
              }
              mayUseToken {
                parentsOwnToken
                inheritFromParent
              }
              authorizationKind {
                isSigned
                isProved
                verificationKeyHash
              }
              update {
                appState
                delegate
                zkappUri
                votingFor
                tokenSymbol
                verificationKey {
                  hash
                  data
                }
                timing {
                  initialMinimumBalance
                  cliffTime
                  cliffAmount
                  vestingPeriod
                  vestingIncrement
                }
                permissions {
                  editState
                  send
                  receive
                  access
                  setDelegate
                  setPermissions
                  setVerificationKey {
                    auth
                    txnVersion
                  }
                  setZkappUri
                  editActionState
                  setTokenSymbol
                  incrementNonce
                  setVotingFor
                  setTiming
                }
              }
              preconditions {
                validWhile {
                  lower
                  upper
                }
                network {
                  snarkedLedgerHash
                  blockchainLength {
                    lower
                    upper
                  }
                  minWindowDensity {
                    lower
                    upper
                  }
                  totalCurrency {
                    lower
                    upper
                  }
                  globalSlotSinceGenesis {
                    lower
                    upper
                  }
                  stakingEpochData {
                    seed
                    startCheckpoint
                    lockCheckpoint
                    epochLength {
                      lower
                      upper
                    }
                    ledger {
                      hash
                      totalCurrency {
                        lower
                        upper
                      }
                    }
                  }
                  nextEpochData {
                    seed
                    startCheckpoint
                    lockCheckpoint
                    epochLength {
                      lower
                      upper
                    }
                    ledger {
                      hash
                      totalCurrency {
                        lower
                        upper
                      }
                    }
                  }
                }
                account {
                  balance {
                    lower
                    upper
                  }
                  nonce {
                    lower
                    upper
                  }
                  receiptChainHash
                  delegate
                  state
                  actionState
                  provedState
                  isNew
                }
              }
            }
          }
        }
      }
    }
  }
}"""

BLOCK = """query Block($stateHash: String, $height: Int) {
  block(stateHash: $stateHash, height: $height) {
    stateHash
    commandTransactionCount
    creatorAccount {
      publicKey
    }
    protocolState {
      previousStateHash
      consensusState {
        blockHeight
        epoch
        slot
        slotSinceGenesis
        blockCreator
        coinbaseReceiever
        stakingEpochData {
          epochLength
          seed
          ledger {
            hash
          }
        }
        nextEpochData {
          seed
          ledger {
            hash
          }
        }
      }
      blockchainState {
        date
        utcDate
        snarkedLedgerHash
        stagedLedgerHash
      }
    }
    snarkJobs {
      prover
      fee
      workIds
    }
    transactions {
      coinbase
      coinbaseReceiverAccount {
        publicKey
      }
      feeTransfer {
        recipient
        fee
        type
      }
      userCommands {
        id
        hash
        kind
        nonce
        source {
          publicKey
        }
        receiver {
          publicKey
        }
        amount
        fee
        memo
        failureReason
      }
      zkappCommands {
        id
        hash
        failureReason {
          index
          failures
        }
        zkappCommand {
          memo
          feePayer {
            authorization
            body {
              publicKey
              fee
              nonce
              validUntil
            }
          }
          accountUpdates {
            authorization {
              signature
              proof
            }
            body {
              publicKey
              tokenId
              callDepth
              callData
              actions
              events
              incrementNonce
              useFullCommitment
              implicitAccountCreationFee
              balanceChange {
                magnitude
                sgn
              }
              mayUseToken {
                parentsOwnToken
                inheritFromParent
              }
              authorizationKind {
                isSigned
                isProved
                verificationKeyHash
              }
              update {
                appState
                delegate
                zkappUri
                votingFor
                tokenSymbol
                verificationKey {
                  hash
                  data
                }
                timing {
                  initialMinimumBalance
                  cliffTime
                  cliffAmount
                  vestingPeriod
                  vestingIncrement
                }
                permissions {
                  editState
                  send
                  receive
                  access
                  setDelegate
                  setPermissions
                  setVerificationKey {
                    auth
                    txnVersion
                  }
                  setZkappUri
                  editActionState
                  setTokenSymbol
                  incrementNonce
                  setVotingFor
                  setTiming
                }
              }
              preconditions {
                validWhile {
                  lower
                  upper
                }
                network {
                  snarkedLedgerHash
                  blockchainLength {
                    lower
                    upper
                  }
                  minWindowDensity {
                    lower
                    upper
                  }
                  totalCurrency {
                    lower
                    upper
                  }
                  globalSlotSinceGenesis {
                    lower
                    upper
                  }
                  stakingEpochData {
                    seed
                    startCheckpoint
                    lockCheckpoint
                    epochLength {
                      lower
                      upper
                    }
                    ledger {
                      hash
                      totalCurrency {
                        lower
                        upper
                      }
                    }
                  }
                  nextEpochData {
                    seed
                    startCheckpoint
                    lockCheckpoint
                    epochLength {
                      lower
                      upper
                    }
                    ledger {
                      hash
                      totalCurrency {
                        lower
                        upper
                      }
                    }
                  }
                }
                account {
                  balance {
                    lower
                    upper
                  }
                  nonce {
                    lower
                    upper
                  }
                  receiptChainHash
                  delegate
                  state
                  actionState
                  provedState
                  isNew
                }
              }
            }
          }
        }
      }
    }
  }
}"""

GET_PEERS = """query Peers {
  getPeers {
    peerId
    host
    libp2pPort
  }
}"""

POOLED_USER_COMMANDS = """query PooledUserCommands($publicKey: PublicKey) {
  pooledUserCommands(publicKey: $publicKey) {
    id
    hash
    kind
    nonce
    amount
    fee
    validUntil
    token
    feeToken
    from
    to
    source {
      publicKey
    }
    receiver {
      publicKey
    }
    memo
    failureReason
  }
}"""

POOLED_ZKAPP_COMMANDS = """query PooledZkappCommands($publicKey: PublicKey) {
  pooledZkappCommands(publicKey: $publicKey) {
    id
    hash
    zkappCommand {
      memo
      feePayer {
        body {
          publicKey
          fee
          nonce
          validUntil
        }
      }
    }
    failureReason {
      index
      failures
    }
  }
}"""

TRANSACTION_STATUS = """query TransactionStatus($payment: ID, $zkappTransaction: ID) {
  transactionStatus(payment: $payment, zkappTransaction: $zkappTransaction)
}"""

GENESIS_CONSTANTS = """query GenesisConstants {
  genesisConstants {
    genesisTimestamp
    coinbase
    accountCreationFee
  }
}"""

TRACKED_ACCOUNTS = """query TrackedAccounts {
  trackedAccounts {
    publicKey
    balance {
      total
    }
  }
}"""

SNARK_POOL = """query SnarkPool {
  snarkPool {
    fee
    prover
    workIds
  }
}"""

FORK_CONFIG = """query ForkConfig {
  fork_config
}"""

SEND_PAYMENT = """mutation SendPayment($input: SendPaymentInput!, $signature: SignatureInput) {
  sendPayment(input: $input, signature: $signature) {
    payment {
      id
      hash
      kind
      nonce
      source {
        publicKey
      }
      receiver {
        publicKey
      }
      amount
      fee
      memo
    }
  }
}"""

SEND_DELEGATION = """mutation SendDelegation($input: SendDelegationInput!, $signature: SignatureInput) {
  sendDelegation(input: $input, signature: $signature) {
    delegation {
      id
      hash
      kind
      nonce
      source {
        publicKey
      }
      receiver {
        publicKey
      }
      amount
      fee
      memo
    }
  }
}"""

SEND_ZKAPP = """mutation SendZkapp($input: SendZkappInput!) {
  sendZkapp(input: $input) {
    zkapp {
      id
      hash
      zkappCommand {
        memo
        feePayer {
          body {
            publicKey
            fee
            nonce
            validUntil
          }
        }
      }
      failureReason {
        index
        failures
      }
    }
  }
}"""

UNLOCK_ACCOUNT = """mutation UnlockAccount($input: UnlockInput!) {
  unlockAccount(input: $input) {
    publicKey
  }
}"""

SET_SNARK_WORKER = """mutation SetSnarkWorker($input: SetSnarkWorkerInput!) {
  setSnarkWorker(input: $input) {
    lastSnarkWorker
  }
}"""

SET_SNARK_WORK_FEE = """mutation SetSnarkWorkFee($fee: UInt64!) {
  setSnarkWorkFee(input: {fee: $fee}) {
    lastFee
  }
}"""

# Deprecated aliases: GET_ACCOUNT takes an optional $token, and
# POOLED_USER_COMMANDS an optional $publicKey.
GET_ACCOUNT_WITH_TOKEN = GET_ACCOUNT
POOLED_USER_COMMANDS_ALL = POOLED_USER_COMMANDS

# Every document of the specification, for the conformance test.
ALL_DOCUMENTS = [
    SYNC_STATUS,
    DAEMON_STATUS,
    DAEMON_METRICS,
    NETWORK_ID,
    GET_ACCOUNT,
    BEST_CHAIN,
    GENESIS_BLOCK,
    BLOCK,
    GET_PEERS,
    POOLED_USER_COMMANDS,
    POOLED_ZKAPP_COMMANDS,
    TRANSACTION_STATUS,
    GENESIS_CONSTANTS,
    TRACKED_ACCOUNTS,
    SNARK_POOL,
    FORK_CONFIG,
    SEND_PAYMENT,
    SEND_DELEGATION,
    SEND_ZKAPP,
    UNLOCK_ACCOUNT,
    SET_SNARK_WORKER,
    SET_SNARK_WORK_FEE,
]
