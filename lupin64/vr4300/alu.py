from .common import *

from nmigen import *


class ALUAbort(Enum):
    OK            = 0
    OverflowCheck = 1


class ALU(Elaboratable):
    def __init__(self):
        self.i_shift_op  = Signal(decoder=ALUShift)
        self.i_adder_op  = Signal(decoder=ALUAdder)
        self.i_logic_op  = Signal(decoder=ALULogic)
        self.i_resultmux = Signal(decoder=ALUResultMux)

        self.i_src_reg_1 = Signal(32)
        self.i_src_reg_2 = Signal(32)
        self.i_dest_reg  = Signal(decoder=Register)

        self.i_ovf_check = Signal()
        self.i_cry_write = Signal()

        self.o_result    = Signal(32)
        self.o_dest_reg  = Signal(decoder=Register)

        self.o_emu_abort = Signal(decoder=ALUAbort)

    def elaborate(self, platform):
        m = Module()

        # ALU outputs
        adder     = Signal(33)
        shift     = Signal(32)
        logic     = Signal(32)
        resultmux = Signal(32)
        carry     = Signal()

        # Barrel shift 
        shift_in  = Signal(32)
        # TODO: can we shorten a path by moving this into the register file?
        m.d.comb += shift_in.eq(Mux(self.i_resultmux == ALUResultMux.ShiftLeft, self.i_src_reg_1[::-1], self.i_src_reg_1))
        with m.Switch(self.i_shift_op):
            with m.Case(ALUShift.Logical):
                m.d.comb += shift.eq(shift_in >> self.i_src_reg_2[:6])
            with m.Case(ALUShift.Arith):
                m.d.comb += shift.eq(shift_in.as_signed() >> self.i_src_reg_2[:6])

        # Add/Subtract
        with m.Switch(self.i_adder_op):
            with m.Case(ALUAdder.Add):
                m.d.comb += adder.eq(self.i_src_reg_1 + self.i_src_reg_2)
            with m.Case(ALUAdder.Sub):
                m.d.comb += adder.eq(self.i_src_reg_1 - self.i_src_reg_2)

        # Logic
        with m.Switch(self.i_logic_op):
            with m.Case(ALULogic.AND):
                m.d.comb += logic.eq(self.i_src_reg_1 & self.i_src_reg_2)
            with m.Case(ALULogic.OR):
                m.d.comb += logic.eq(self.i_src_reg_1 | self.i_src_reg_2)
            with m.Case(ALULogic.XOR):
                m.d.comb += logic.eq(self.i_src_reg_1 ^ self.i_src_reg_2)
            with m.Case(ALULogic.NOR):
                m.d.comb += logic.eq(~(self.i_src_reg_1 | self.i_src_reg_2))

        # Result multiplexer
        with m.Switch(self.i_resultmux):
            with m.Case(ALUResultMux.ShiftLeft, ALUResultMux.ShiftRight):
                m.d.comb += Cat(resultmux, carry).eq(shift)
            with m.Case(ALUResultMux.Adder):
                m.d.comb += Cat(resultmux, carry).eq(adder)
            with m.Case(ALUResultMux.Logic):
                m.d.comb += Cat(resultmux, carry).eq(logic)

        # Result flags
        negative  = Signal()
        zero      = Signal()
        overflow  = Signal()

        m.d.comb += [
            negative.eq(resultmux[31]),
            zero.eq(resultmux == 0),
            overflow.eq((Cat(self.i_src_reg_1[31], self.i_src_reg_2[31], adder[31]) == 0b100) | (Cat(self.i_src_reg_1[31], self.i_src_reg_2[31], adder[31]) == 0b011))
        ]

        m.d.sync += [
            # Abort on overflow when overflow checking is enabled.
            self.o_emu_abort.eq((self.i_ovf_check & overflow)),

            self.o_result.eq(Mux(self.i_cry_write, carry, resultmux))
        ]

        return m
