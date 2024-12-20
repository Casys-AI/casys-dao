from pyteal import *

def approval_program():
    """
    ASA Approval Program for CaSys Token
    """
    
    # Global state keys
    manager_key = Bytes("manager")
    reserve_key = Bytes("reserve")
    
    # Operations
    op_initialize = Bytes("initialize")
    op_transfer = Bytes("transfer")
    op_modify_manager = Bytes("modify_manager")
    
    @Subroutine(TealType.uint64)
    def is_manager():
        return And(
            Global.group_size() == Int(1),
            Txn.sender() == App.globalGet(manager_key)
        )
    
    # Initialize the contract
    on_initialize = Seq([
        Assert(Txn.application_args.length() == Int(2)),
        App.globalPut(manager_key, Txn.application_args[1]),
        App.globalPut(reserve_key, Global.zero_address()),
        Return(Int(1))
    ])
    
    # Handle ASA transfers
    on_transfer = Seq([
        Assert(Txn.application_args.length() == Int(4)),
        # Add transfer logic here
        Return(Int(1))
    ])
    
    # Modify manager address
    on_modify_manager = Seq([
        Assert(is_manager()),
        Assert(Txn.application_args.length() == Int(2)),
        App.globalPut(manager_key, Txn.application_args[1]),
        Return(Int(1))
    ])
    
    # Main router
    program = Cond(
        [Txn.application_id() == Int(0), on_initialize],
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(is_manager())],
        [Txn.on_completion() == OnComplete.UpdateApplication, Return(is_manager())],
        [Txn.on_completion() == OnComplete.CloseOut, Return(Int(0))],
        [Txn.on_completion() == OnComplete.OptIn, Return(Int(1))],
        [Txn.application_args[0] == op_transfer, on_transfer],
        [Txn.application_args[0] == op_modify_manager, on_modify_manager]
    )
    
    return program

def clear_state_program():
    """
    ASA Clear State Program for CaSys Token
    """
    return Return(Int(1))

if __name__ == "__main__":
    # Compile approval program
    with open("approval.teal", "w") as f:
        compiled = compileTeal(approval_program(), mode=Mode.Application, version=6)
        f.write(compiled)
    
    # Compile clear state program
    with open("clear.teal", "w") as f:
        compiled = compileTeal(clear_state_program(), mode=Mode.Application, version=6)
        f.write(compiled)
