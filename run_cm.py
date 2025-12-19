
import sys
import os
# Ensure src is in path to find csrlite
sys.path.insert(0, os.path.abspath('src'))

from csrlite import load_plan, study_plan_to_cm_summary, study_plan_to_cm_listing

try:
    plan = load_plan("plan_cm_xyz123.yaml")
    
    print("Generating Summary...")
    res_sum = study_plan_to_cm_summary(plan)
    print(f"Summary files generated: {res_sum}")
    import os
    print(f"Expected location: {os.path.abspath(res_sum[0])}")
    
    print("Generating Listing...")
    res_list = study_plan_to_cm_listing(plan)
    print(f"Listing files generated: {res_list}")
    
except Exception as e:
    import traceback
    traceback.print_exc()
