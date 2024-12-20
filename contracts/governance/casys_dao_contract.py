from pyteal import *

def approval_program():
    """
    Governance System Approval Program
    """
    
    # Global state keys
    token_id_key = Bytes("token_id")
    proposal_counter_key = Bytes("proposal_counter")
    proposal_threshold_key = Bytes("proposal_threshold")
    voting_period_key = Bytes("voting_period")
    execution_delay_key = Bytes("execution_delay")
    quorum_key = Bytes("quorum")
    collateral_app_id = Bytes("collateral_app_id")
    token_app_id = Bytes("token_app_id")
    
    # Types de propositions
    prop_type_yield = Bytes("yield_rate")
    prop_type_mint = Bytes("mint_tokens")
    prop_type_ratio = Bytes("collateral_ratio")

    # Local state keys (per proposal)
    proposal_type_key = Bytes("type")
    proposal_value_key = Bytes("value")
    proposal_title_key = Bytes("title")
    proposal_description_key = Bytes("description")
    proposal_start_key = Bytes("start_time")
    proposal_end_key = Bytes("end_time")
    proposal_execution_key = Bytes("execution_time")
    proposal_executed_key = Bytes("executed")
    proposal_votes_for_key = Bytes("votes_for")
    proposal_votes_against_key = Bytes("votes_against")
    
    # Operations
    op_initialize = Bytes("initialize")
    op_create_proposal = Bytes("create_proposal")
    op_vote = Bytes("vote")
    op_execute = Bytes("execute")
    
    @Subroutine(TealType.uint32)
    def is_proposal_active(proposal_id):
        return And(
            App.localGet(Int(proposal_id), proposal_start_key) <= Global.latest_timestamp(),
            Global.latest_timestamp() < App.localGet(Int(proposal_id), proposal_end_key)
        )
    
    @Subroutine(TealType.uint32)
    def can_execute_proposal(proposal_id):
        return And(
            Global.latest_timestamp() >= App.localGet(Int(proposal_id), proposal_execution_key),
            Not(App.localGet(Int(proposal_id), proposal_executed_key))
        )
    
    @Subroutine(TealType.uint32)
    def has_quorum(proposal_id):
        total_votes = App.localGet(Int(proposal_id), proposal_votes_for_key) + \
                     App.localGet(Int(proposal_id), proposal_votes_against_key)
        return total_votes >= App.globalGet(quorum_key)
    
    @Subroutine(TealType.uint32)
    def validate_proposal_value(proposal_type, value):
        return Cond(
            [proposal_type == prop_type_yield,
             And(
                 value >= Int(0),
                 value <= Int(1000),  # Max 100%
                 # Vérifier que la valeur est un multiple de 1 (0.1%)
                 value % Int(1) == Int(0)
             )],
            [proposal_type == prop_type_mint,
             And(
                 value > Int(0),
                 value <= Int(2**31 - 1)  # Max safe value for int32
             )],
            [proposal_type == prop_type_ratio,
             And(
                 value >= Int(0),
                 value <= Int(10000),  # Max 1000%
                 # Vérifier que la valeur est un multiple de 1 (0.1%)
                 value % Int(1) == Int(0)
             )]
        )

    @Subroutine(TealType.uint32)
    def execute_proposal_action(proposal_id):
        proposal_type = App.localGet(Int(proposal_id), proposal_type_key)
        proposal_value = App.localGet(Int(proposal_id), proposal_value_key)
        
        # Valider la valeur avant l'exécution
        Assert(validate_proposal_value(proposal_type, proposal_value))
        
        return Cond(
            [proposal_type == prop_type_yield,
             Seq([
                 InnerTxnBuilder.Begin(),
                 InnerTxnBuilder.SetFields({
                     TxnField.type_enum: TxnType.ApplicationCall,
                     TxnField.application_id: App.globalGet(collateral_app_id),
                     TxnField.application_args: [Bytes("update_yield_rate"), Itob(proposal_value)]
                 }),
                 InnerTxnBuilder.Submit(),
                 Int(1)
             ])],
            
            [proposal_type == prop_type_mint,
             Seq([
                 InnerTxnBuilder.Begin(),
                 InnerTxnBuilder.SetFields({
                     TxnField.type_enum: TxnType.ApplicationCall,
                     TxnField.application_id: App.globalGet(token_app_id),
                     TxnField.application_args: [Bytes("mint"), Itob(proposal_value)]
                 }),
                 InnerTxnBuilder.Submit(),
                 Int(1)
             ])],
            
            [proposal_type == prop_type_ratio,
             Seq([
                 InnerTxnBuilder.Begin(),
                 InnerTxnBuilder.SetFields({
                     TxnField.type_enum: TxnType.ApplicationCall,
                     TxnField.application_id: App.globalGet(collateral_app_id),
                     TxnField.application_args: [Bytes("update_collateral_ratio"), Itob(proposal_value)]
                 }),
                 InnerTxnBuilder.Submit(),
                 Int(1)
             ])]
        )
    
    # Initialize the contract
    on_initialize = Seq([
        Assert(Txn.application_args.length() == Int(8)),
        App.globalPut(token_id_key, Btoi(Txn.application_args[1])),
        App.globalPut(proposal_threshold_key, Btoi(Txn.application_args[2])),
        App.globalPut(voting_period_key, Btoi(Txn.application_args[3])),
        App.globalPut(execution_delay_key, Btoi(Txn.application_args[4])),
        App.globalPut(quorum_key, Btoi(Txn.application_args[5])),
        App.globalPut(collateral_app_id, Btoi(Txn.application_args[6])),
        App.globalPut(token_app_id, Btoi(Txn.application_args[7])),
        App.globalPut(proposal_counter_key, Int(0)),
        Return(Int(1))
    ])
    
    # Create a new proposal
    on_create_proposal = Seq([
        Assert(Txn.application_args.length() == Int(6)),  # op, type, value, title, description, execution_delay
        Assert(AssetHolding.balance(Txn.sender(), App.globalGet(token_id_key)) >= 
              App.globalGet(proposal_threshold_key)),
        
        # Calculate timestamps
        start_time := Global.latest_timestamp(),
        end_time := start_time + App.globalGet(voting_period_key),
        execution_time := end_time + Btoi(Txn.application_args[5]),
        
        # Store proposal data
        App.localPut(Txn.sender(), proposal_type_key, Txn.application_args[1]),
        App.localPut(Txn.sender(), proposal_value_key, Btoi(Txn.application_args[2])),
        App.localPut(Txn.sender(), proposal_title_key, Txn.application_args[3]),
        App.localPut(Txn.sender(), proposal_description_key, Txn.application_args[4]),
        App.localPut(Txn.sender(), proposal_start_key, start_time),
        App.localPut(Txn.sender(), proposal_end_key, end_time),
        App.localPut(Txn.sender(), proposal_execution_key, execution_time),
        App.localPut(Txn.sender(), proposal_executed_key, Int(0)),
        App.localPut(Txn.sender(), proposal_votes_for_key, Int(0)),
        App.localPut(Txn.sender(), proposal_votes_against_key, Int(0)),
        
        # Increment proposal counter
        App.globalPut(
            proposal_counter_key,
            App.globalGet(proposal_counter_key) + Int(1)
        ),
        Return(Int(1))
    ])
    
    # Vote on a proposal
    on_vote = Seq([
        Assert(Txn.application_args.length() == Int(3)),  # op, proposal_id, vote
        proposal_id := Btoi(Txn.application_args[1]),
        vote_value := Btoi(Txn.application_args[2]),
        
        Assert(is_proposal_active(proposal_id)),
        Assert(Or(vote_value == Int(0), vote_value == Int(1))),
        
        # Get voter's token balance
        token_balance := AssetHolding.balance(Txn.sender(), App.globalGet(token_id_key)),
        Assert(token_balance.hasValue()),
        Assert(token_balance.value() > Int(0)),
        
        # Record vote
        If(vote_value == Int(1),
            App.localPut(
                Int(proposal_id),
                proposal_votes_for_key,
                App.localGet(Int(proposal_id), proposal_votes_for_key) + token_balance.value()
            ),
            App.localPut(
                Int(proposal_id),
                proposal_votes_against_key,
                App.localGet(Int(proposal_id), proposal_votes_against_key) + token_balance.value()
            )
        ),
        Return(Int(1))
    ])
    
    # Execute a proposal
    on_execute = Seq([
        Assert(Txn.application_args.length() == Int(2)),  # op, proposal_id
        proposal_id := Btoi(Txn.application_args[1]),
        
        Assert(can_execute_proposal(proposal_id)),
        Assert(has_quorum(proposal_id)),
        
        # Check if proposal passed
        votes_for := App.localGet(Int(proposal_id), proposal_votes_for_key),
        votes_against := App.localGet(Int(proposal_id), proposal_votes_against_key),
        Assert(votes_for > votes_against),
        
        # Execute proposal action
        execute_proposal_action(proposal_id),
        
        # Mark proposal as executed
        App.localPut(Int(proposal_id), proposal_executed_key, Int(1)),
        Return(Int(1))
    ])
    
    # Main router
    program = Cond(
        [Txn.application_id() == Int(0), on_initialize],
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(Int(0))],
        [Txn.on_completion() == OnComplete.UpdateApplication, Return(Int(0))],
        [Txn.on_completion() == OnComplete.CloseOut, Return(Int(1))],
        [Txn.on_completion() == OnComplete.OptIn, Return(Int(1))],
        [Txn.application_args[0] == op_create_proposal, on_create_proposal],
        [Txn.application_args[0] == op_vote, on_vote],
        [Txn.application_args[0] == op_execute, on_execute]
    )
    
    return program

def clear_state_program():
    """
    Governance Clear State Program
    """
    return Return(Int(1))

if __name__ == "__main__":
    # Compile approval program
    with open("governance_approval.teal", "w") as f:
        compiled = compileTeal(approval_program(), mode=Mode.Application, version=6)
        f.write(compiled)
    
    # Compile clear state program
    with open("governance_clear.teal", "w") as f:
        compiled = compileTeal(clear_state_program(), mode=Mode.Application, version=6)
        f.write(compiled)
