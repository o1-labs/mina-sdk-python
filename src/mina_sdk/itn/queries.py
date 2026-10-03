"""GraphQL documents for the daemon's ITN server.

These are the documents of ``spec/itn-operations.graphql`` (a copy of
o1-labs/mina-sdk-spec, whose CI validates them against the daemon's
``schema_itn``); ``tests/test_spec.py`` checks that they stay identical. Use
them with ``ItnClient.execute_query`` for custom selections.
"""

AUTH = """query Auth {
  auth {
    serverUuid
    signerSequenceNumber
    libp2pPort
    peerId
    isBlockProducer
  }
}"""

SLOTS_WON = """query SlotsWon {
  slotsWon
}"""

INTERNAL_LOGS = """query InternalLogs($startLogId: Int!) {
  internalLogs(startLogId: $startLogId) {
    id
    timestamp
    message
    metadata {
      item
      value
    }
    process
  }
}"""

FLUSH_INTERNAL_LOGS = """mutation FlushInternalLogs($endLogId: Int!) {
  flushInternalLogs(endLogId: $endLogId)
}"""

SCHEDULE_PAYMENTS = """mutation SchedulePayments($input: PaymentsDetails!) {
  schedulePayments(input: $input)
}"""

SCHEDULE_ZKAPP_COMMANDS = """mutation ScheduleZkappCommands($input: ZkappCommandsDetails!) {
  scheduleZkappCommands(input: $input)
}"""

STOP_SCHEDULED_TRANSACTIONS = """mutation StopScheduledTransactions($handle: String!) {
  stopScheduledTransactions(handle: $handle)
}"""

UPDATE_GATING = """mutation UpdateGating($input: GatingUpdate!) {
  updateGating(input: $input)
}"""

STOP_DAEMON = """mutation StopDaemon($delaySeconds: Int, $cleanConfig: Boolean) {
  stopDaemon(delaySeconds: $delaySeconds, cleanConfig: $cleanConfig)
}"""

ZKAPP_COMMAND_LIMIT = """mutation ZkappCommandLimit($limit: Int) {
  zkAppCommandLimit(limit: $limit)
}"""

# The following operations need a daemon with MinaProtocol/mina#19616; older
# daemons answer them with a GraphQL error.

COMMIT_ID = """query CommitId {
  auth {
    commitId
  }
}"""

SCHEDULED_TRANSACTIONS = """query ScheduledTransactions {
  scheduledTransactions
}"""

SCHEDULE_PAYMENTS_WITH_HANDLE = """mutation SchedulePaymentsWithHandle($input: PaymentsDetails!, $handle: String!) {
  schedulePayments(input: $input, handle: $handle)
}"""

SCHEDULE_ZKAPP_COMMANDS_WITH_HANDLE = """mutation ScheduleZkappCommandsWithHandle($input: ZkappCommandsDetails!, $handle: String!) {
  scheduleZkappCommands(input: $input, handle: $handle)
}"""

CREATE_ACCOUNTS = """mutation CreateAccounts($input: CreateAccountsDetails!, $handle: String) {
  createAccounts(input: $input, handle: $handle) {
    handle
    accounts {
      publicKey
      privateKey
    }
  }
}"""

# Every ITN document of the specification, for the conformance test.
ALL_ITN_DOCUMENTS = [
    AUTH,
    SLOTS_WON,
    INTERNAL_LOGS,
    FLUSH_INTERNAL_LOGS,
    SCHEDULE_PAYMENTS,
    SCHEDULE_ZKAPP_COMMANDS,
    STOP_SCHEDULED_TRANSACTIONS,
    UPDATE_GATING,
    STOP_DAEMON,
    ZKAPP_COMMAND_LIMIT,
    COMMIT_ID,
    SCHEDULED_TRANSACTIONS,
    SCHEDULE_PAYMENTS_WITH_HANDLE,
    SCHEDULE_ZKAPP_COMMANDS_WITH_HANDLE,
    CREATE_ACCOUNTS,
]
