from pyteal import *

def approval_program():
    on_creation = Seq([
        Assert(Txn.application_args.length() == Int(15)),
        App.globalPut(Bytes("Game"), Txn.application_args[0]),
        App.globalPut(Bytes("Creator"), Txn.sender()),
        App.globalPut(Bytes("Escrow"), Txn.application_args[1]),
        App.globalPut(Bytes("Winner"), Txn.sender()),
        App.globalPut(Bytes("BidCount"), Int(0)),
        App.globalPut(Bytes("RoundStart"), Btoi(Txn.application_args[2])),
        App.globalPut(Bytes("RoundEnd"), Btoi(Txn.application_args[11])),
        App.globalPut(Bytes("Price"), Btoi(Txn.application_args[3])),
        App.globalPut(Bytes("Multiplier"), Btoi(Txn.application_args[4])),
        App.globalPut(Bytes("Timer"), Btoi(Txn.application_args[5])),
        App.globalPut(Bytes("TimerFirst"), Btoi(Txn.application_args[6])),
        App.globalPut(Bytes("TimerSecond"), Btoi(Txn.application_args[7])),
        App.globalPut(Bytes("FeesFirst"), Btoi(Txn.application_args[8])),
        App.globalPut(Bytes("FeesSecond"), Btoi(Txn.application_args[9])),
        App.globalPut(Bytes("Dividend"), Btoi(Txn.application_args[10])),
        App.globalPut(Bytes("SeedAmount"), Btoi(Txn.application_args[12])),
        App.globalPut(Bytes("PlusMinusFirst"), Btoi(Txn.application_args[13])),
        App.globalPut(Bytes("PlusMinusSecond"), Btoi(Txn.application_args[14])),
        App.globalPut(Bytes("Pot"), Int(0)),
        Return(Int(1))
    ])

    # All the global get methods
    get_local_bids = App.localGet(Int(1), Bytes("Bids"))
    get_creator = App.globalGet(Bytes("Creator"))
    get_escrow = App.globalGet(Bytes("Escrow"))
    get_game = App.globalGet(Bytes("Game"))
    get_pot = App.globalGet(Bytes("Pot"))
    get_bid_count = App.globalGet(Bytes("BidCount"))
    get_price = App.globalGet(Bytes("Price"))
    get_multiplier = App.globalGet(Bytes("Multiplier"))
    get_round_end = App.globalGet(Bytes("RoundEnd"))
    get_timer = App.globalGet(Bytes("Timer"))
    get_timer_first = App.globalGet(Bytes("TimerFirst"))
    get_timer_second = App.globalGet(Bytes("TimerSecond"))
    get_fees_first = App.globalGet(Bytes("FeesFirst"))
    get_fees_second = App.globalGet(Bytes("FeesSecond"))
    get_plus_minus_first = App.globalGet(Bytes("PlusMinusFirst"))
    get_plus_minus_second = App.globalGet(Bytes("PlusMinusSecond"))

    is_creator = Gtxn[1].sender() == get_creator
    is_not_creator = Gtxn[1].sender() != get_creator

    # Compare the current price to determine if first bid by player
    is_normal_bid = And(
        is_not_creator,
        Gtxn[1].amount() == get_price
    )

    # Compare the current price to determine if first bid by player
    is_first_bid = And(
        is_not_creator,
        Gtxn[1].amount() == get_price + get_price * get_fees_first / Int(100)
    )

    # Compare the current price to determine if second bid by player
    is_second_bid = And(
        is_not_creator,
        Gtxn[1].amount() == get_price + get_price * get_fees_second / Int(100)
    )

    # Initial seed bid by creator
    is_seed_bid = And(
        is_creator,
        get_pot == Int(0)
    )

    # Bids can only be grouped transaction and called by creator. Goes into escrow address
    is_valid_bid = And(
        Global.group_size() == Int(2),
        Or(is_normal_bid, is_first_bid, is_second_bid, is_seed_bid),
        Gtxn[0].sender() == get_creator,
        Gtxn[1].receiver() == get_escrow,
        Gtxn[1].type_enum() == TxnType.Payment
    )

    normal_bid = Seq([
                    App.globalPut(Bytes("BidCount"), get_bid_count + Int(1)),
                    App.globalPut(Bytes("Price"), Gtxn[1].amount() + (Gtxn[1].amount() * get_multiplier / Int(10000))),
                    App.globalPut(Bytes("RoundEnd"), get_round_end + get_timer)
                ])
    first_bid = Seq([
                    App.globalPut(Bytes("BidCount"), get_bid_count + Int(1)),
                    App.globalPut(Bytes("Price"), Gtxn[1].amount() + (Gtxn[1].amount() * get_multiplier / Int(10000))),
                    App.globalPut(Bytes("RoundEnd"), get_round_end + get_timer_first * get_plus_minus_first - get_timer_first)
                ])
    second_bid = Seq([
                    App.globalPut(Bytes("BidCount"), get_bid_count + Int(1)),
                    App.globalPut(Bytes("Price"), Gtxn[1].amount() + (Gtxn[1].amount() * get_multiplier / Int(10000))),
                    App.globalPut(Bytes("RoundEnd"), get_round_end + get_timer_second * get_plus_minus_second - get_timer_second)
                ])

    # Update winner, pot amount and local bids of player
    on_bid = Seq([
        Assert(is_valid_bid),
        App.globalPut(Bytes("Pot"), get_pot + Gtxn[1].amount()),
        App.globalPut(Bytes("Winner"), Gtxn[1].sender()),
        App.localPut(Int(1), Bytes("Bids"), get_local_bids + Gtxn[1].amount()),
        If(is_normal_bid, normal_bid),
        If(is_first_bid, first_bid),
        If(is_second_bid, second_bid),
        Return(Int(1))
    ])

    # Can only delete app by creator if pot is empty
    on_delete = Seq([
        Assert(Txn.sender() == get_creator),
        Assert(get_pot == Int(0)),
        Return(Int(1))
    ])

    on_closeout = Seq([
        Return(Int(1))
    ])

    # Update escrow address after creating
    on_update = Seq([
        Assert(Txn.sender() == get_creator),
        Assert(Txn.application_args.length() == Int(1)),
        App.globalPut(Bytes("Escrow"), Txn.application_args[0]),
        Return(Int(1)) 
    ])

    # Opt into contract
    on_opt = Seq([
        App.localPut(Int(0), Bytes("Bids"), Int(0)),
        App.localPut(Int(0), Bytes("BidCount"), Int(0)),
        Return(Int(1))
    ])

    # Drain the escrow - Can only be called by algofair
    on_drain = Seq([
        Assert(Global.group_size() == Int(2)),
        Assert(Gtxn[0].sender() == get_creator),
        Assert(Gtxn[1].sender() == get_escrow),
        Assert(Gtxn[1].amount() == Int(0)),
        Assert(Gtxn[1].receiver() == get_game),
    	Assert(Gtxn[1].close_remainder_to() == get_game),
    	Return(Int(1))
    ])

    program = Cond(
        [Txn.application_id() == Int(0), on_creation],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
        [Txn.on_completion() == OnComplete.UpdateApplication, on_update],
        [Txn.on_completion() == OnComplete.CloseOut, on_closeout],
        [Txn.on_completion() == OnComplete.OptIn, on_opt],
        [Bytes("bid") == Txn.application_args[0], on_bid],
	    [Bytes("drain") == Txn.application_args[0], on_drain]
    )

    return program

def clear_state_program():
    program = Seq([
        Return(Int(1))
    ])
    return program

with open('snatch_approval.teal', 'w') as f:
    compiled = compileTeal(approval_program(), Mode.Application)
    f.write(compiled)

with open('snatch_clear_state.teal', 'w') as f:
    compiled = compileTeal(clear_state_program(), Mode.Application)
    f.write(compiled)
