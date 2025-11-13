# -------------------------------------------------------
# utilities.py
# -------------------------------------------------------

import vsc
import cocotb

from ref_model import sat_filter_ref_model
from cocotb.triggers import RisingEdge, ReadOnly


# !!! THIS FILE MUST NOT BE CHANGED !!!


async def check_results(dut):
    """ Checker coroutine to validate DUT output.
    """

    # Uncomment to print debug messages
    # cocotb.log.setLevel(10)     #DEBUG=10, INFO=20

    # Instance of the saturation filter reference model
    ref_model = sat_filter_ref_model()
    await RisingEdge(dut.clk)

    while True:

        await ReadOnly()

        # Wait for a valid input signal
        while not dut.in_data.value.is_resolvable:
            await ReadOnly()
            await RisingEdge(dut.clk)

        cocotb.log.debug(f"DUT's input: {dut.in_data.value}")

        # Get expected output value from reference model
        if dut.in_valid.value == 1:
            ref_model_input = dut.in_data.value.integer
        else:
            ref_model_input = 0

        ref_model_output = ref_model.operation(ref_model_input)

        cocotb.log.debug(f"REf. Model, in: {ref_model_input}, out: {ref_model_output}.")

        # Wait for setting output
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)

        # Wait for a valid output signal
        while not dut.out_data.value.is_resolvable:
            await RisingEdge(dut.clk)

        # Check result
        assert dut.out_data.value == ref_model_output, \
            f"Saturation Filter output is incorrect: {dut.out_data.value.integer} != {ref_model_output}. For input: {ref_model_input}."
        pass

        cocotb.log.debug(f"Input: {ref_model_input}, Output: {dut.out_data.value.integer}, Output (Ref. Model): {ref_model_output}")


def create_coverage_report(name):
    """ Method that will generate the coverage report files.
    - 'name' : coverage file name
    """

    # Writing coverage report in (.txt format)
    f = open(f'sim_build/{name}_cov.txt', "w")
    vsc.report_coverage(fp=f, details=True)
    f.close()

    # writing coverage report in xml-format
    filename = f'sim_build/{name}_cov.xml'
    fmt = "xml"
    libucis = None

    vsc.write_coverage_db(
        filename,
        fmt,
        libucis
    )

    # For each file only information regarding the test will show
    vsc.impl.coverage_registry.CoverageRegistry.clear()