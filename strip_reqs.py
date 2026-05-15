import re

def strip_versions(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if line.strip() and not line.startswith('#'):
            # Strip anything after >=, <=, or == unless it's the opentelemetry fix
            if 'opentelemetry-exporter-gcp-monitoring' in line:
                new_lines.append(line)
            else:
                new_lines.append(re.sub(r'[>=<]=?.*', '', line).strip() + '\n')
        else:
            new_lines.append(line)
            
    with open(file_path, 'w') as f:
        f.writelines(new_lines)

strip_versions('ml/requirements.txt')
strip_versions('backend/requirements.txt')
print("Stripped versions from requirements.txt")
