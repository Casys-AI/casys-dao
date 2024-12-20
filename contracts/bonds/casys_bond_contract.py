from pyteal import *

def approval_program():
    """
    Bond System Approval Program
    """
    
    # Global state keys
    token_id_key = Bytes("token_id")
    bond_counter_key = Bytes("bond_counter")
    interest_rate_key = Bytes("interest_rate")
    min_lock_time_key = Bytes("min_lock_time")
    manager_key = Bytes("manager")
    
    # Local state keys (per user)
    bond_amount_key = Bytes("bond_amount")
    lock_time_key = Bytes("lock_time")
    
    # Operations
    op_initialize = Bytes("initialize")
    op_create_bond = Bytes("create_bond")
    op_redeem_bond = Bytes("redeem_bond")
    op_update_rate = Bytes("update_rate")
    
    @Subroutine(TealType.uint32)
    def is_manager():
        return And(
            Global.group_size() == Int(1),
            Txn.sender() == App.globalGet(manager_key)
        )
    
    @Subroutine(TealType.uint32)
    def is_bond_mature(lock_time):
        return Global.latest_timestamp() >= (
            lock_time + App.globalGet(min_lock_time_key)
        )
    
    @Subroutine(TealType.uint32)
    def calculate_interest(amount, lock_time):
        time_locked = Global.latest_timestamp() - lock_time
        interest_rate = App.globalGet(interest_rate_key)
        # Éviter le dépassement en divisant d'abord
        yearly_factor = time_locked / Int(31536000)  # secondes par an
        rate_factor = interest_rate / Int(100)
        return amount + (amount * yearly_factor * rate_factor)
    
    # Initialize the contract
    on_initialize = Seq([
        Assert(Txn.application_args.length() == Int(5)),
        App.globalPut(token_id_key, Btoi(Txn.application_args[1])),
        App.globalPut(interest_rate_key, Btoi(Txn.application_args[2])),
        App.globalPut(min_lock_time_key, Btoi(Txn.application_args[3])),
        App.globalPut(manager_key, Txn.application_args[4]),
        App.globalPut(bond_counter_key, Int(0)),
        Return(Int(1))
    ])
    
    # Create a new bond
    on_create_bond = Seq([
        Assert(Txn.application_args.length() == Int(2)),
        Assert(Gtxn[1].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[1].xfer_asset() == App.globalGet(token_id_key)),
        App.localPut(Txn.sender(), bond_amount_key, Gtxn[1].asset_amount()),
        App.localPut(Txn.sender(), lock_time_key, Global.latest_timestamp()),
        App.globalPut(
            bond_counter_key,
            App.globalGet(bond_counter_key) + Int(1)
        ),
        Return(Int(1))
    ])
    
    # Redeem a bond
    on_redeem_bond = Seq([
        Assert(App.localGet(Txn.sender(), bond_amount_key) > Int(0)),
        Assert(is_bond_mature(App.localGet(Txn.sender(), lock_time_key))),
        # Calculate interest
        interest = calculate_interest(
            App.localGet(Txn.sender(), bond_amount_key),
            App.localGet(Txn.sender(), lock_time_key)
        ),
        # Clear local state
        App.localDel(Txn.sender(), bond_amount_key),
        App.localDel(Txn.sender(), lock_time_key),
        # Update bond counter
        App.globalPut(
            bond_counter_key,
            App.globalGet(bond_counter_key) - Int(1)
        ),
        Return(Int(1))
    ])
    
    # Update interest rate
    on_update_rate = Seq([
        Assert(is_manager()),
        Assert(Txn.application_args.length() == Int(2)),
        App.globalPut(interest_rate_key, Btoi(Txn.application_args[1])),
        Return(Int(1))
    ])
    
    # Main router
    program = Cond(
        [Txn.application_id() == Int(0), on_initialize],
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(is_manager())],
        [Txn.on_completion() == OnComplete.UpdateApplication, Return(is_manager())],
        [Txn.on_completion() == OnComplete.CloseOut, Return(Int(0))],
        [Txn.on_completion() == OnComplete.OptIn, Return(Int(1))],
        [Txn.application_args[0] == op_create_bond, on_create_bond],
        [Txn.application_args[0] == op_redeem_bond, on_redeem_bond],
        [Txn.application_args[0] == op_update_rate, on_update_rate]
    )
    
    return program

def clear_state_program():
    """
    Bond System Clear State Program
    """
    return Return(Int(1))

if __name__ == "__main__":
    # Compile approval program
    with open("bond_approval.teal", "w") as f:
        compiled = compileTeal(approval_program(), mode=Mode.Application, version=6)
        f.write(compiled)
    
    # Compile clear state program
    with open("bond_clear.teal", "w") as f:
        compiled = compileTeal(clear_state_program(), mode=Mode.Application, version=6)
        f.write(compiled)
