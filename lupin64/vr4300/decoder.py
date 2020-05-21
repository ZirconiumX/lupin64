from vr4300.common import *

from enum import Enum, unique

from nmigen import *
from nmigen.back import rtlil

@unique
class Instruction(Enum):
    """A MIPS Instruction"""
    SPECIAL = 0b000000 # Decoded
    REGIMM  = 0b000001
    J       = 0b000010
    JAL     = 0b000011
    BEQ     = 0b000100
    BNE     = 0b000101
    BLEZ    = 0b000110
    BGTZ    = 0b000111
    ADDI    = 0b001000 # Decoded
    ADDIU   = 0b001001 # Decoded
    SLTI    = 0b001010 # Decoded
    SLTIU   = 0b001011 # Decoded
    ANDI    = 0b001100
    ORI     = 0b001101
    XORI    = 0b001110
    LUI     = 0b001111
    COP0    = 0b010000
    COP1    = 0b010001
    COP2    = 0b010010
    BEQL    = 0b010100
    BNEL    = 0b010101
    BLEZL   = 0b010110
    BGTZL   = 0b010111
    DADDI   = 0b011000
    DADDIU  = 0b011001
    LDL     = 0b011010
    LDR     = 0b011011
    LB      = 0b100000
    LH      = 0b100001
    LWL     = 0b100010
    LW      = 0b100011
    LBU     = 0b100100
    LHU     = 0b100101
    LWR     = 0b100110
    LWU     = 0b100111
    SB      = 0b101000
    SH      = 0b101001
    SWL     = 0b101010
    SW      = 0b101011
    SDL     = 0b101100
    SDR     = 0b101101
    SWR     = 0b101110
    CACHE   = 0b101111
    LL      = 0b110000
    LWC1    = 0b110001
    LWC2    = 0b110010
    LLD     = 0b110100
    LDC1    = 0b110101
    LDC2    = 0b110110
    LD      = 0b110111
    SC      = 0b111000
    SWC1    = 0b111001
    SWC2    = 0b111010
    SCD     = 0b111100
    SDC1    = 0b111101
    SDC2    = 0b111110
    SD      = 0b111111


@unique
class Function(Enum):
    """A MIPS Instruction with op = 0"""
    SLL     = 0b000000 # Decoded
    SRL     = 0b000010 # Decoded
    SRA     = 0b000011 # Decoded
    SLLV    = 0b000100 # Decoded
    SRLV    = 0b000110 # Decoded
    SRAV    = 0b000111 # Decoded
    JR      = 0b001000
    JALR    = 0b001001
    SYSCALL = 0b001100
    BREAK   = 0b001101
    SYNC    = 0b001111
    MFHI    = 0b010000
    MTHI    = 0b010001
    MFLO    = 0b010010
    MTLO    = 0b010011
    DSLLV   = 0b010100
    DSRLV   = 0b010110
    DSRAV   = 0b010111
    MULT    = 0b011000
    MULTU   = 0b011001
    DIV     = 0b011010
    DIVU    = 0b011011
    DMULT   = 0b011100
    DMULTU  = 0b011101
    DDIV    = 0b011110
    DDIVU   = 0b011111
    ADD     = 0b100000 # Decoded
    ADDU    = 0b100001 # Decoded
    SUB     = 0b100010 # Decoded
    SUBU    = 0b100011 # Decoded
    AND     = 0b100100
    OR      = 0b100101
    XOR     = 0b100110
    NOR     = 0b100111
    SLT     = 0b101010 # Decoded
    SLTU    = 0b101011 # Decoded
    DADD    = 0b101100
    DADDU   = 0b101101
    DSUB    = 0b101110
    DSUBU   = 0b101111
    TGE     = 0b110000
    TGEU    = 0b110001
    TLT     = 0b110010
    TLTU    = 0b110011
    TEQ     = 0b110100
    TNE     = 0b110110
    DSLL    = 0b111000
    DSRL    = 0b111010
    DSRA    = 0b111011
    DSLL32  = 0b111100
    DSRL32  = 0b111110
    DSRA32  = 0b111111


@unique
class DecoderAbort(Enum):
    OK                 = 0
    IllegalInstruction = 1


class Decoder(Elaboratable):
    def __init__(self):
        self.i_insn = Signal(32)

        self.o_shift_op  = Signal(decoder=ALUShift)
        self.o_adder_op  = Signal(decoder=ALUAdder)
        self.o_logic_op  = Signal(decoder=ALULogic)
        self.o_resultmux = Signal(decoder=ALUResultMux)

        self.o_src_reg_1 = Signal(decoder=Register)
        self.o_src_reg_2 = Signal(decoder=Register)
        self.o_dest_reg  = Signal(decoder=Register)

        self.o_immediate = Signal(signed(32))

        self.o_use_imm   = Signal()
        self.o_ovf_check = Signal()
        self.o_cry_write = Signal()

        self.o_emu_abort = Signal(decoder=DecoderAbort)

    def elaborate(self, platform):
        m = Module()

        # Instruction subfields
        op = Signal(decoder=Instruction)
        rs = Signal(decoder=Register)
        rt = Signal(decoder=Register)
        rd = Signal(decoder=Register)
        sa = Signal(5)
        funct = Signal(decoder=Function)
        regimm = Signal(5)
        imm16 = Signal(signed(16))
        imm26 = Signal(26)

        m.d.comb += [
            Cat(funct, sa, rd, rt, rs, op).eq(self.i_insn),
            Cat(regimm, imm16).eq(self.i_insn[:21]),
            imm26.eq(self.i_insn[:26])
        ]

        # Defaults
        m.d.sync += [
            # ALU defaults.
            self.o_shift_op.eq(ALUShift.Logical),
            self.o_adder_op.eq(ALUAdder.Add),
            self.o_logic_op.eq(ALULogic.AND),
            self.o_resultmux.eq(ALUResultMux.ShiftLeft),
            # Don't right-to-left flip the argument.
            self.o_flip.eq(0),
            # Don't use the immediate field.
            self.o_immediate.eq(0),
            self.o_use_imm.eq(0),
            # Default to illegal instructions aborting emulation.
            self.o_emu_abort.eq(1),
            # Only a few instructions trap on overflow.
            self.o_ovf_check.eq(0),
        ]

        with m.Switch(op):
            with m.Case(Instruction.SPECIAL):
                with m.Switch(funct):
                    with m.Case(
                        Function.SLL, Function.SRL, Function.SRA,
                        Function.SLLV, Function.SRLV, Function.SRAV
                    ):
                        is_arithmetic = Signal()
                        is_immediate = Signal()

                        m.d.comb += [
                            # Arithmetic shifts shift in the sign bit.
                            is_arithmetic.eq(funct.matches(Function.SRA, Function.SRAV)),
                            # Immediate shifts need the immediate decoded and placed somewhere.
                            is_immediate.eq(funct.matches(Function.SLL, Function.SRL, Function.SRA)),
                        ]

                        m.d.sync += [
                            # Implement left-shift in terms of flip, right-shift, flip.
                            self.o_flip.eq(funct.matches(Function.SLL, Function.SLLV)),
                            # Put the shift immediate in the immediate pipeline register.
                            self.o_immediate.eq(sa),
                            # Select the appropriate ALU op.
                            self.o_shift_op.eq(Mux(is_arithmetic, ALUShift.Arith, ALUShift.Logical)),
                            # These are legal instructions.
                            self.o_emu_abort.eq(0),
                        ]

                    with m.Case(
                        Function.ADD, Function.ADDU, Function.SUB, Function.SUBU,
                    ):
                        m.d.comb += [
                            # Select the appropriate ALU op.
                            self.o_adder_op.eq(Mux(funct.matches(Function.SUB, Function.SUBU), ALUAdder.Sub, ALUAdder.Add)),
                            # These are legal instructions.
                            self.o_emu_abort.eq(0),
                            # "signed" instructions trap on overflow here.
                            self.o_ovf_check.eq(funct.matches(Function.ADD, Function.SUB))
                        ]

                    with m.Case(
                        Function.SLT, Function.SLTU
                    ):
                        is_signed = Signal()

                        m.d.comb += [
                            is_signed.eq(funct.matches(Function.SLT))
                        ]

                        m.d.sync += [
                            # Because MIPS always sign-extends values, we can treat this as an unconditional 64-bit operation.
                            self.o_is_64bit.eq(1),
                            # Implement comparisons in terms of subtraction.
                            self.o_adder_op.eq(ALUAdder.Sub),
                            # These are legal instructions.
                            self.o_emu_abort.eq(0)
                        ]

            with m.Case(
                Instruction.ADDI, Instruction.ADDIU, Instruction.DADDI, Instruction.DADDIU
            ):
                is_signed = Signal()

                m.d.comb += [
                    # Overflow on "signed" instructions raises an exception.
                    is_signed.eq(funct.matches(Function.ADDI, Function.DADDI)),
                    # Load the immediate register
                    self.o_immediate.eq(imm16),
                    self.o_use_imm.eq(1),
                    # Select the appropriate ALU op.
                    self.o_adder_op.eq(ALUAdder.Add),
                    # These are legal instructions.
                    self.o_ri_except.eq(0),
                    # "signed" instructions trap on overflow here.
                    self.o_ovf_check.eq(is_signed)
                ]

            with m.Case(
                Instruction.SLTI, Instruction.SLTIU
            ):
                is_signed = Signal()

                m.d.comb += [
                    is_signed.eq(funct.matches(Function.SLTI)),

                    # Load the immediate register
                    self.o_immediate.eq(imm16),
                    self.o_use_imm.eq(1),
                    # Implement comparisons in terms of subtraction.
                    self.o_adder_op.eq(ALUAdder.Sub),
                    # These are legal instructions.
                    self.o_emu_abort.eq(0)
                ]

        return m

rtlil.convert(Decoder())
