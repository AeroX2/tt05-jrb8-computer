`default_nettype none

module tt_um_aerox2_jrb8_computer #( parameter MAX_COUNT = 24'd10_000_000 ) (
    input  wire [7:0] ui_in,    // Dedicated inputs - connected to the input switches
    output wire [7:0] uo_out,   // Dedicated outputs - connected to the 7 segment display
    input  wire [7:0] uio_in,   // IOs: Bidirectional Input path
    output wire [7:0] uio_out,  // IOs: Bidirectional Output path
    output wire [7:0] uio_oe,   // IOs: Bidirectional Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // will go high when the design is enabled
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);
	wire rst = !rst_n;

	reg [7:0] mar;
	reg [7:0] areg;
	reg [7:0] breg;
	reg [7:0] creg;
	reg [7:0] oreg;
	reg [7:0] ireg;

	wire [7:0] rom;
	wire [7:0] ram;

	// Input/output pins
	assign uio_oe[0] = 1;
	assign uio_oe[1] = 1;
	assign uio_oe[2] = 0;
	assign uio_oe[3] = 0;
	assign uio_oe[4] = 1;
	assign uio_oe[5] = 1;
	assign uio_oe[6] = 1;
	assign uio_oe[7] = 0;

	assign uio_out[0] = cs_rom;
	assign uio_out[1] = mosi;
	assign uio_out[2] = 0;
	assign uio_out[3] = sclk;
	assign uio_out[4] = cs_ram;
	assign uio_out[5] = 0;
	assign uio_out[6] = 0;
	assign uio_out[7] = 0;

	// Internal registers
	// A, B, C, D, O, I
	always @(posedge clk, posedge rst) begin
		if (rst) begin
			mar <= 0;
			areg <= 0;
			breg <= 0;
			creg <= 0;
			oreg <= 0;
			ireg <= 0;
		end else if (clk) begin
			if (mari)
				mar <= databus;
			if (ai)
				areg <= databus;
			if (bi)
				breg <= databus;
			if (ci)
				creg <= databus;
			if (oi)
				oreg <= databus;
			ireg <= ui_in;
		end
	end
	assign uo_out = oreg;

	// TODO: This seems a little unclean.
	wire raw_ramil = inflags == 2;

	wire cs;
	wire cs_rom = romo ? cs : 1;
	wire cs_ram = (raw_ramil || ramo) ? cs : 1;

	wire mosi;
	wire miso = uio_in[2];
	wire sclk;

	wire [7:0] spi_data;
	wire spi_executing;
	wire spi_done;
	// SPI Ram for ROM memory
	spi spi_module(
		.clk(clk),
		.rst(rst),

		.databus(databus),

		.start(spi_executing),
		.done(spi_done),
		.write(raw_ramil),
		.address(romo ? pc : mar),
		.data(spi_data),

		.sclk(sclk),
		.cs(cs),
		.mosi(mosi),
		.miso(miso)
	);

	wire input_we;
	wire highbits_we;
    wire pcinflag;
	wire [15:0] pc;
    wire [15:0] pcin;

	// CU
	wire [7:0] cins;
	cu cu_module(
		.clk(clk),
		.rst(rst),
		.halt(halt),
		.input_we(input_we),
		.highbits_we(highbits_we),
		
		.spi_executing(spi_executing),
		.spi_done(spi_done),

		.irin(databus),

		.pcinflag(pcinflag),
		.pcin(pcin),
		.pc(pc),
		
		.inflags(inflags),
		.outflags(outflags),
		.cuout(cins)
	);

	// CU decoding the instruction
	wire [4:0] inflags;
	wire [3:0] outflags;

	wire [15:0] in_decoder = 8'b0000_0001 << (input_we ? inflags : 16'h00);
	wire [7:0] out_decoder = 8'b0000_0001 << outflags;

	wire oi = in_decoder[1];
	wire ramil = in_decoder[2];
	wire mari = in_decoder[3];
	wire ai = in_decoder[4];
	wire bi = in_decoder[5];
	wire ci = in_decoder[6];
	wire jmpi = in_decoder[7];
	// wire ramih = in_decoder[7];
	wire halt = in_decoder[15];

	wire io = out_decoder[1];
	wire ao = out_decoder[2];
	wire bo = out_decoder[3];
	wire co = out_decoder[4];
	wire romo = out_decoder[5];
	wire ramo = out_decoder[6];

	// Databus
	wire [7:0] aluout;
	wire [7:0] rom_or_ram = (romo || ramo) ? spi_data : 8'h00;
	wire [7:0] iorg = io ? ireg : 8'h00;
	wire [7:0] corg = co ? creg : 8'h00;
	wire [7:0] databus = rom_or_ram | aluout | iorg | corg;

	// ALU
	wire aluo = ao | bo;
	wire overout;
	wire carryout;
	wire cmpo;
	alu alu_module(
		.a(areg),
		.b(breg),
		.carryin(cflag),
		.oe(aluo),
		.cins(cins),
		.aluout(aluout),
		.overout(overout),
		.carryout(carryout),
		.cmpo(cmpo)
	);

	// CMP
	wire zflag;
	wire oflag;
	wire cflag;
	wire sflag;
	cmp cmp_module(
		.cmpin(databus),
		.overflow(overout),
		.carry(carryout),
		.clk(clk),
		.rst(rst),
		.zflag(zflag),
		.oflag(oflag),
		.cflag(cflag),
		.sflag(sflag),
		.we(cmpo)
	);
  
	// JMP
	jmp jmp_module(
		.cins(cins),
		.pcin(pc),
		.databus(databus),
		.clk(clk),
		.rst(rst),
		.zflag(zflag),
		.oflag(oflag),
		.cflag(cflag),
		.sflag(sflag),
		.pcoe(pcinflag),
		.pcout(pcin),
		.oe(jmpi),
		.highbits_we(highbits_we)
	);
endmodule
