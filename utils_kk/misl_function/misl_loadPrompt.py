import yaml
import os

def load_prompt(prompt_name: str, filename: str = None) -> str:

    base_dir = os.path.join(os.getcwd(), r"utils_kk/prompts")
    path = os.path.join(base_dir, filename)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        prompts = yaml.safe_load(f)

    if prompt_name not in prompts:
        raise ValueError(f"Prompt '{prompt_name}' not found in {path}.")

    prompt_entry = prompts[prompt_name]

    if "template" not in prompt_entry:
        raise ValueError(f"Prompt '{prompt_name}' is missing a 'template' field.")

    return prompt_entry["template"]

if __name__ == "__main__":
    print(load_prompt(prompt_name="intent_classification_template", 
                filename="prompts_intentClassification.yml"))