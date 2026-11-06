from app.services.search_manager import search_manager
import time

print("Iniciando pesquisa...")
task_id = search_manager.start_search(termos=["esgoto"], ufs=["SP"])
print("Task iniciada:", task_id)

for _ in range(5):
    status = search_manager.get_status(task_id)
    print("Status:", status.get('status'), "- UF:", status.get('uf_atual'))
    time.sleep(2)

print("Teste completado.")
