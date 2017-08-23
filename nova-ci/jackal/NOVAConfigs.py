import collections

KernelConfig = collections.namedtuple("KernelConfig", "name kernel_repo kernel_config_file")
TestConfig = collections.namedtuple("TestConfig", "name config test_class timeout")
NovaConfig = collections.namedtuple("NovaConfig", "name module_args")


nova_module_args="""
data_csum={data_csum}
data_parity={data_parity}
dram_struct_csum={dram_struct_csum}
inplace_data_updates={inplace_data_updates}
metadata_csum={metadata_csum}
wprotect={wprotect}
"""

def decode_flags(flags):
    
    (data_csum,
     data_parity,
     dram_struct_csum,
     inplace_data_updates,
     metadata_csum,
     wprotect) = flags.split("-")

    return nova_module_args.format(**locals())

def build_configs():
    r = []
    for data_csum in [0,1]:
        for data_parity in [0,1]:
            for dram_struct_csum in [0,1]:
                for inplace_data_updates in [0,1]:
                    for metadata_csum in [0,1]:
                        for wprotect in [0,1]:
                            r.append(NovaConfig(name="baseline-{data_csum}-{data_parity}-{dram_struct_csum}-{inplace_data_updates}-{metadata_csum}-{wprotect}".format(**locals()),
                                                module_args=nova_module_args.format(**locals())))

    return r


if __name__ == "__main__":
    import sys
    print decode_flags(sys.argv[1])
