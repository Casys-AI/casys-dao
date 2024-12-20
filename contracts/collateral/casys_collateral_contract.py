from pyteal import *

def approval_program():
    """
    CaSys Collateral Management Contract
    Handles stablecoin collateral, yield distribution, and ratio management
    """
    
    # Global state keys
    stablecoin_id_key = Bytes("stablecoin_id")
    token_id_key = Bytes("token_id")
    collateral_ratio_key = Bytes("collateral_ratio")
    total_collateral_key = Bytes("total_collateral")
    last_distribution_key = Bytes("last_distribution")
    distribution_rate_key = Bytes("distribution_rate")
    distribution_period_key = Bytes("distribution_period")
    manager_key = Bytes("manager")
    
    # Operations
    op_initialize = Bytes("initialize")
    op_deposit_collateral = Bytes("deposit_collateral")
    op_withdraw_collateral = Bytes("withdraw_collateral")
    op_distribute_yield = Bytes("distribute_yield")
    op_update_ratio = Bytes("update_ratio")
    op_update_rate = Bytes("update_rate")
    
    @Subroutine(TealType.uint64)
    def is_manager():
        return And(
            Global.group_size() == Int(1),
            Txn.sender() == App.globalGet(manager_key)
        )
    
    @Subroutine(TealType.uint64)
    def can_distribute():
        return Global.latest_timestamp() >= (
            App.globalGet(last_distribution_key) + 
            App.globalGet(distribution_period_key)
        )
    
    # Initialize the contract
    on_initialize = Seq([
        Assert(Txn.application_args.length() == Int(8)),
        App.globalPut(stablecoin_id_key, Btoi(Txn.application_args[1])),
        App.globalPut(token_id_key, Btoi(Txn.application_args[2])),
        App.globalPut(collateral_ratio_key, Btoi(Txn.application_args[3])),
        App.globalPut(distribution_rate_key, Btoi(Txn.application_args[4])),
        App.globalPut(distribution_period_key, Btoi(Txn.application_args[5])),
        App.globalPut(manager_key, Txn.application_args[6]),
        App.globalPut(total_collateral_key, Int(0)),
        App.globalPut(last_distribution_key, Global.latest_timestamp()),
        Return(Int(1))
    ])
    
    # Deposit collateral
    on_deposit_collateral = Seq([
        Assert(Txn.application_args.length() == Int(2)),
        Assert(Gtxn[1].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[1].xfer_asset() == App.globalGet(stablecoin_id_key)),
        
        # Update total collateral
        App.globalPut(
            total_collateral_key,
            App.globalGet(total_collateral_key) + Gtxn[1].asset_amount()
        ),
        Return(Int(1))
    ])
    
    # Withdraw collateral
    on_withdraw_collateral = Seq([
        Assert(Txn.application_args.length() == Int(2)),
        Assert(is_manager()),
        withdrawal_amount := Btoi(Txn.application_args[1]),
        
        # Check if withdrawal maintains minimum collateral ratio
        Assert(
            App.globalGet(total_collateral_key) - withdrawal_amount >= 
            App.globalGet(collateral_ratio_key)
        ),
        
        # Update total collateral
        App.globalPut(
            total_collateral_key,
            App.globalGet(total_collateral_key) - withdrawal_amount
        ),
        Return(Int(1))
    ])
    
    # Distribute yield
    on_distribute_yield = Seq([
        Assert(can_distribute()),
        
        # Calculate distribution amount
        distribution_amount := (
            App.globalGet(total_collateral_key) * 
            App.globalGet(distribution_rate_key)
        ) / Int(10000),
        
        # Update last distribution time
        App.globalPut(last_distribution_key, Global.latest_timestamp()),
        
        Return(Int(1))
    ])
    
    # Update collateral ratio
    on_update_ratio = Seq([
        Assert(Txn.application_args.length() == Int(2)),
        Assert(is_manager()),
        new_ratio := Btoi(Txn.application_args[1]),
        
        # Verify new ratio is valid
        Assert(new_ratio > Int(0)),
        Assert(new_ratio <= Int(10000)),  # Max 100%
        
        App.globalPut(collateral_ratio_key, new_ratio),
        Return(Int(1))
    ])
    
    # Update distribution rate
    on_update_rate = Seq([
        Assert(Txn.application_args.length() == Int(2)),
        Assert(is_manager()),
        new_rate := Btoi(Txn.application_args[1]),
        
        # Verify new rate is valid
        Assert(new_rate > Int(0)),
        Assert(new_rate <= Int(1000)),  # Max 10%
        
        App.globalPut(distribution_rate_key, new_rate),
        Return(Int(1))
    ])
    
    # Main router
    program = Cond(
        [Txn.application_id() == Int(0), on_initialize],
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(is_manager())],
        [Txn.on_completion() == OnComplete.UpdateApplication, Return(is_manager())],
        [Txn.on_completion() == OnComplete.CloseOut, Return(Int(0))],
        [Txn.on_completion() == OnComplete.OptIn, Return(Int(1))],
        [Txn.application_args[0] == op_deposit_collateral, on_deposit_collateral],
        [Txn.application_args[0] == op_withdraw_collateral, on_withdraw_collateral],
        [Txn.application_args[0] == op_distribute_yield, on_distribute_yield],
        [Txn.application_args[0] == op_update_ratio, on_update_ratio],
        [Txn.application_args[0] == op_update_rate, on_update_rate]
    )
    
    return program

def clear_state_program():
    """
    CaSys Collateral Clear State Program
    """
    return Return(Int(1))

if __name__ == "__main__":
    # Compile approval program
    with open("collateral_approval.teal", "w") as f:
        compiled = compileTeal(approval_program(), mode=Mode.Application, version=6)
        f.write(compiled)
    
    # Compile clear state program
    with open("collateral_clear.teal", "w") as f:
        compiled = compileTeal(clear_state_program(), mode=Mode.Application, version=6)
        f.write(compiled)
