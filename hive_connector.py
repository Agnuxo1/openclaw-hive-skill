import json
import asyncio
import websockets
# Assuming openclaw.sdk is a placeholder for the actual agent SDK structure
# In a real deployment, this would import from the agent's core library
class Log:
    @staticmethod
    def info(msg): print(f"[INFO] {msg}")
    @staticmethod
    def success(msg): print(f"[SUCCESS] {msg}")
    @staticmethod
    def warning(msg): print(f"[WARNING] {msg}")
    @staticmethod
    def error(msg): print(f"[ERROR] {msg}")

class Skill:
    def __init__(self):
        self.agent = None # To be injected

class HiveConnector(Skill):
    def __init__(self):
        self.hive_url = "wss://hive.p2pclaw.com"
        self.my_role = "UNASSIGNED"
        self.current_project = None
        self.shared_memory = {} # "La Rueda" local cache

    async def on_start(self):
        """Se ejecuta automáticamente al iniciar el Agente."""
        Log.info("🔌 Iniciando Protocolo Enjambre P2PCLAW...")
        await self.connect_to_hive()

    async def connect_to_hive(self):
        try:
            async with websockets.connect(self.hive_url) as websocket:
                # 1. Handshake y Recepción de Estado (Estatuto III.1)
                # In a real WebSocket P2P, we might need to send an init handshake first or wait for a peer
                # For this connector logic, we assume standard Gun.js / WebSocket behavior simulated or bridged
                
                # Senda generic "HELLO" or auth if needed by the specific P2P bridge
                # For Gun.js, connection is automatic, but we might want to subscribe to data.
                
                Log.info(f"Connected to {self.hive_url}")
                
                # Mocking reception for logical flow if strictly Gun.js, 
                # but if using a bridge server (like the one proposed earlier or direct Gun wire protocol), adaptation is key.
                # Here we implement the logic as requested:
                
                # response = await websocket.recv()
                # hive_state = json.loads(response)
                
                # if hive_state.get('type') == 'INIT_STATE':
                #    await self.select_project(websocket, hive_state['data']['projects'])
                
                # Bucle principal de escucha
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self.handle_hive_message(data)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            Log.error(f"Connection error: {e}")
            # Retry logic could go here

    async def select_project(self, ws, projects):
        """Selecciona el Top 10 basado en capacidades del agente."""
        my_skills = self.agent.get_capabilities() if hasattr(self.agent, 'get_capabilities') else []
        best_match = None
        highest_score = -1

        # Lógica de Selección (Punto 1 y 2)
        for proj in projects:
            match_score = sum(1 for tag in proj.get('tags', []) if tag in my_skills)
            if match_score > highest_score:
                highest_score = match_score
                best_match = proj

        # Si no hay coincidencia, elegir el Top 1 por defecto
        if not best_match and projects:
            best_match = projects[0]
            self.allocate_resources(mode="HYBRID") # Activar Regla 50/50
        elif best_match:
            self.allocate_resources(mode="FULL") # Activar Bola de Nieve 100%

        if best_match:
            # Unirse al proyecto
            join_msg = {
                "type": "JOIN_PROJECT",
                "agentId": getattr(self.agent, 'id', 'unknown_agent'),
                "projectId": best_match['id']
            }
            await ws.send(json.dumps(join_msg))
            self.current_project = best_match.get('title', 'Unknown Project')
            Log.success(f"✅ Unido a investigación: {self.current_project}")

    def allocate_resources(self, mode):
        """Gestión de Tributo de Cómputo (Estatuto III.3)"""
        if not hasattr(self.agent, 'set_compute_power'):
            Log.warning("Agent does not support compute adjustment.")
            return

        if mode == "FULL":
            self.agent.set_compute_power(100, target="HIVE_NETWORK")
            Log.info("🚀 Coincidencia Total: 100% CPU asignada al enjambre.")
        else:
            self.agent.set_compute_power(50, target="HIVE_NETWORK")
            self.agent.set_compute_power(50, target="LOCAL_TASK")
            Log.warning("⚠️ Modo Híbrido: 50% Donación / 50% Tarea Propia.")

    async def check_wheel(self, component_name):
        """Consultar La Rueda antes de crear nada (Estatuto IV)"""
        if not hasattr(self.agent, 'mcp_query'):
             return None
             
        # Esta función se inyecta en el proceso creativo del agente
        response = await self.agent.mcp_query(f"p2p://hive/memory?item={component_name}")
        if response and response.get('exists'):
            Log.info(f"🛑 ¡ALTO! Componente '{component_name}' detectado en La Rueda. Descargando...")
            return response.get('code')
        else:
            return None

    async def handle_hive_message(self, msg):
        # Gestión de Roles Dinámicos (Estatuto III.2)
        if msg.get('type') == 'ROLE_UPDATE':
            self.my_role = msg.get('role') # DIRECTOR o COLABORADOR
            Log.info(f"👑 Rol Actualizado: {self.my_role}")
            
            if hasattr(self.agent, 'activate_mode'):
                if self.my_role == "DIRECTOR":
                    await self.agent.activate_mode("LEADERSHIP")
                else:
                    await self.agent.activate_mode("FOLLOWER")
