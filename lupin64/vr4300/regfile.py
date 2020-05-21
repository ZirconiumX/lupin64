from .common import *

from nmigen import *

class RegisterFile(Elaboratable):
    def __init__(self):
        self.i_shift_op  = Signal(decoder=ALUShift)
        self.i_adder_op  = Signal(decoder=ALUAdder)
        self.i_logic_op  = Signal(decoder=ALULogic)
        self.i_resultmux = Signal(decoder=ALUResultMux)
        self.i_src_reg_1 = Signal(decoder=Register)
        self.i_src_reg_2 = Signal(decoder=Register)
        self.i_immediate = Signal(signed(32))

        self.i_use_imm   = Signal()
        self.i_flip      = Signal()
        self.i_ovf_check = Signal()
        self.i_cry_write = Signal()

        self.o_shift_op  = Signal(decoder=ALUShift)
        self.o_adder_op  = Signal(decoder=ALUAdder)
        self.o_logic_op  = Signal(decoder=ALULogic)
        self.o_resultmux = Signal(decoder=ALUResultMux)
        self.o_src_reg_1 = Signal(32)
        self.o_src_reg_2 = Signal(32)

        self.o_ovf_check = Signal()
        self.o_cry_write = Signal()

    def elaborate(self, platform):
        m = Module()

        regfile = Memory(width=32, depth=32)

        m.submodules["rf_wr"]  = rf_wr = regfile.write_port()
        m.submodules["rf_rd1"] = rf_rd1 = regfile.read_port()
        m.submodules["rf_rd2"] = rf_rd2 = regfile.read_port()

        m.d.comb += [
            rf_rd1.addr.eq(self.i_src_reg_1),
            rf_rd2.addr.eq(self.i_src_reg_2),
        ]

        m.d.sync += [
            self.o_src_reg_1.eq(Mux(self.i_src_reg_1 == Register.ZERO, 0, rf_rd1.data)),
            self.o_src_reg_2.eq(Mux(self.i_src_reg_2 == Register.ZERO, 0, Mux(i_use_imm, self.i_immediate, rf_rd2.data))),

            self.o_shift_op.eq(self.i_shift_op),
            self.o_adder_op.eq(self.i_adder_op),
            self.o_logic_op.eq(self.i_logic_op),
            self.o_resultmux.eq(self.i_resultmux),

            self.o_ovf_check.eq(self.i_ovf_check),
            self.o_cry_write.eq(self.i_cry_write)
        ]

        return m
