#!/usr/bin/env python3
"""
Demo script showing how to use the TLF YAML framework.

This script demonstrates the basic usage pattern:
1. Load a study configuration with inheritance
2. Generate TLFs using the configuration
"""

import sys
from pathlib import Path

# Add src to path for demo purposes
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tlfyaml import YAMLInheritanceLoader, TLFGenerator


def main():
    """Main demo function."""
    print("TLF YAML Framework Demo")
    print("=" * 50)

    # Setup paths
    examples_dir = Path(__file__).parent
    yaml_dir = examples_dir / "yaml"
    output_dir = examples_dir / "output"

    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)

    print(f"Examples directory: {examples_dir}")
    print(f"YAML configs: {yaml_dir}")
    print(f"Output directory: {output_dir}")
    print()

    # Step 1: Load study configuration
    print("Step 1: Loading study configuration...")
    loader = YAMLInheritanceLoader(config_base_path=yaml_dir)

    try:
        study_config_path = yaml_dir / "study_xyz123.yaml"
        config = loader.load_study_config(str(study_config_path))
        print(f"✓ Successfully loaded study config: {config.study['name']}")
        print(f"  Title: {config.study['title']}")
        print(f"  Data sources: subject ({config.data.subject.source}), observation ({config.data.observation.source})")
        print(f"  TLFs defined: {list(config.tlfs.keys())}")
        print()
    except Exception as e:
        print(f"✗ Error loading configuration: {e}")
        return 1

    # Step 2: Initialize TLF generator
    print("Step 2: Initializing TLF generator...")
    generator = TLFGenerator(config)
    print("✓ TLF generator initialized")
    print()

    # Step 3: Generate individual TLFs
    print("Step 3: Generating individual TLFs...")
    tlf_names = ["ae_summary_by_treatment", "ae_listing_serious"]

    for tlf_name in tlf_names:
        try:
            print(f"  Generating {tlf_name}...")
            output_file = generator.generate_tlf(tlf_name, output_dir=str(output_dir))
            print(f"  ✓ Generated: {output_file}")
        except Exception as e:
            print(f"  ✗ Error generating {tlf_name}: {e}")

    print()

    # Step 4: Generate all TLFs at once
    print("Step 4: Generating all TLFs...")
    try:
        output_files = generator.generate_all_tlfs(output_dir=str(output_dir))
        print(f"✓ Generated {len(output_files)} TLFs:")
        for tlf_name, output_file in output_files.items():
            if output_file.startswith("ERROR:"):
                print(f"  ✗ {tlf_name}: {output_file}")
            else:
                print(f"  ✓ {tlf_name}: {Path(output_file).name}")
    except Exception as e:
        print(f"✗ Error generating all TLFs: {e}")

    print()
    print("Demo completed!")
    print(f"Check the output directory for generated files: {output_dir}")

    return 0


def inspect_config():
    """Additional function to inspect the loaded configuration."""
    print("\nConfiguration Inspection")
    print("=" * 30)

    yaml_dir = Path(__file__).parent / "yaml"
    loader = YAMLInheritanceLoader(config_base_path=yaml_dir)

    study_config_path = yaml_dir / "study_xyz123.yaml"
    config = loader.load_study_config(str(study_config_path))

    print(f"Study: {config.study}")
    print(f"Data Sources: 2 defined")
    print(f"  - subject: {config.data.subject.source} ({config.data.subject.path})")
    print(f"  - observation: {config.data.observation.source} ({config.data.observation.path})")

    if config.treatments:
        print(f"Treatments: {len(config.treatments)} defined")
        for name, trt in config.treatments.items():
            print(f"  - {name}: {trt.name}")

    if config.populations:
        print(f"Populations: {len(config.populations)} defined")
        for name, pop in config.populations.items():
            print(f"  - {name}: {pop.label}")

    print(f"TLFs: {len(config.tlfs)} defined")
    for name, tlf in config.tlfs.items():
        print(f"  - {name}: {tlf.type} - {tlf.title}")


if __name__ == "__main__":
    exit_code = main()

    # Uncomment to see detailed configuration inspection
    # inspect_config()

    sys.exit(exit_code)