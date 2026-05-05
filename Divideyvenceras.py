
import json
import random
import os
from collections import deque
from itertools import permutations

from Entregas import Entrega, validar_entregas
from Viajes import crear_viajes, PESO_MAXIMO, MAX_DELIVERIES_PER_TRIP

# Umbral: si un cuadrante tiene ≤ este número de entregas,
# se resuelve por fuerza bruta sin seguir dividiendo.
UMBRAL_BASE = 2



# CARGA DEL MAPA 

VALORES = {"Camino": 1, "Inicio": 2, "Estacion": 3}


def cargar_mapa(json_path="prueba.json"):
    
    # Lee el JSON del proyecto:
    #   [{"fila": N, "columna": N, "valor": "Camino/Inicio/Estacion"}, ...]
    # Retorna: (matriz, inicio, estaciones)
    
    with open(json_path) as f:
        data = json.load(f)

    max_fila = max(item["fila"] for item in data)
    max_col  = max(item["columna"] for item in data)
    matriz   = [[0] * max_col for _ in range(max_fila)]

    for item in data:
        matriz[item["fila"] - 1][item["columna"] - 1] = VALORES.get(item["valor"], 0)

    inicio     = None
    estaciones = []
    for i, fila in enumerate(matriz):
        for j, celda in enumerate(fila):
            if celda == 2:
                inicio = (i, j)
            elif celda == 3:
                estaciones.append((i, j))

    return matriz, inicio, estaciones


def imprimir_mapa_con_cuadrantes(matriz, cuadrantes, ruta=None, destinos=None):
    """
    Visualiza el mapa marcando la división en cuadrantes.
    Los cuadrantes se muestran con distintos bordes visuales.

    cuadrantes: dict {nombre: [(fila,col), ...]} de celdas por cuadrante
    """
    simbolos  = {0: '██', 1: '  ', 2: ' S', 3: ' E'}
    ruta_set  = set(ruta)    if ruta    else set()
    dest_set  = set(destinos) if destinos else set()

    # Colores ASCII por cuadrante (para diferenciarlos en consola)
    marcas_q  = {}
    etiquetas = ['Q1', 'Q2', 'Q3', 'Q4']
    for i, (nombre, celdas) in enumerate(cuadrantes.items()):
        for celda in celdas:
            marcas_q[celda] = etiquetas[i % 4]

    ancho = len(matriz[0]) * 2 + 2
    print(f"\n  [Mapa con cuadrantes]  S=Inicio  E=Estación  ░░=Ruta  ██=Pared")
    print(f"  {'─'*ancho}")

    for r, fila in enumerate(matriz):
        print("│ ", end="")
        for c, celda in enumerate(fila):
            pos = (r, c)
            if pos in dest_set:
                print("◉◉", end="")
            elif pos in ruta_set:
                print("░░", end="")
            else:
                print(simbolos.get(celda, '??'), end="")
        print(" │")

    print(f"  {'─'*ancho}")


def imprimir_division_cuadrantes(matriz, mid_r, mid_c, grupos, depth=0):
    """
    Muestra visualmente cómo se dividió el mapa y qué entregas
    quedaron en cada cuadrante en un nivel de recursión.
    """
    indent = "  " * depth
    filas  = len(matriz)
    cols   = len(matriz[0])

    nombres = ["Q1 (sup-izq)", "Q2 (sup-der)", "Q3 (inf-izq)", "Q4 (inf-der)"]
    simbolos_q = ["①", "②", "③", "④"]

    print(f"\n{indent}┌─ División nivel {depth} ──────────────────────────────")
    print(f"{indent}│  Mapa {filas}×{cols}  →  corte en fila {mid_r}, col {mid_c}")

    for i, (nombre, indices) in enumerate(zip(nombres, grupos)):
        if indices:
            print(f"{indent}│  {simbolos_q[i]} {nombre}: {len(indices)} entrega/s → índices {indices}")
        else:
            print(f"{indent}│  {simbolos_q[i]} {nombre}: vacío")
    print(f"{indent}└───────────────────────────────────────────────")



#   2: BFS — PATHFINDING


def bfs(matriz, inicio, objetivo):
    """
    BFS para ruta más corta. Mismo comportamiento que
    Proyecto_2_Datos_2.py pero recibe la matriz como parámetro.
    Retorna: lista de celdas (camino) o None si no existe ruta.
    """
    movimientos = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    filas = len(matriz)
    cols  = len(matriz[0])

    visitado = [[False] * cols for _ in range(filas)]
    padre    = [[None]  * cols for _ in range(filas)]
    cola     = deque([inicio])
    visitado[inicio[0]][inicio[1]] = True

    while cola:
        x, y = cola.popleft()
        if (x, y) == objetivo:
            break
        for dx, dy in movimientos:
            nx, ny = x + dx, y + dy
            if (0 <= nx < filas and 0 <= ny < cols
                    and not visitado[nx][ny]
                    and matriz[nx][ny] != 0):
                visitado[nx][ny] = True
                padre[nx][ny]    = (x, y)
                cola.append((nx, ny))

    camino = []
    actual = objetivo
    while actual:
        camino.append(actual)
        actual = padre[actual[0]][actual[1]]
    camino.reverse()

    return camino if (camino and camino[0] == inicio) else None


def _alcanzables(matriz, inicio):
    """BFS completo para saber qué celdas son alcanzables."""
    visitado = set()
    cola     = deque([inicio])
    visitado.add(inicio)
    while cola:
        x, y = cola.popleft()
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = x+dx, y+dy
            if (0 <= nx < len(matriz) and 0 <= ny < len(matriz[0])
                    and (nx,ny) not in visitado
                    and matriz[nx][ny] != 0):
                visitado.add((nx,ny))
                cola.append((nx,ny))
    return visitado


def construir_matrices(matriz, nodos):
    """
    Construye dist[i][j] y rutas[i][j] para todos los pares de nodos.
    nodos[0] = base, nodos[1..n] = estaciones de entregas.
    """
    n     = len(nodos)
    dist  = [[0.0] * n for _ in range(n)]
    rutas = [[[] for _ in range(n)] for _ in range(n)]

    print("\n[BFS] Calculando distancias...", end="")
    for i in range(n):
        for j in range(n):
            if i != j:
                camino = bfs(matriz, nodos[i], nodos[j])
                if camino:
                    dist[i][j]  = len(camino) - 1
                    rutas[i][j] = camino
                else:
                    dist[i][j]  = float('inf')
    print(" listo.")
    return dist, rutas



#   3: DIVIDE Y VENCERÁS


class DivideYVenceras:
    
    # Resuelve el problema de optimización de rutas dividiendo
    # el mapa en cuadrantes de forma recursiva.

    #   - índice de entrega: posición en self.entregas (0-based)
    #   - índice de nodo:    posición en dist_matrix (0=base, 1..n=estaciones)
    #   - bbox:              (min_fila, max_fila, min_col, max_col) del cuadrante actual

    # orden:
    #   resolver(indices, bbox)
    #      len <= UMBRAL → brute_force()     CASO BASE
    #     todos en mismo sub-bbox → brute_force() (evitar recursión infinita)
    #     ├dividir en Q1,Q2,Q3,Q4 por punto medio
    #      resolver() recursivo en cada cuadrante no vacío
    #     combinar() → mejor orden de visitar los cuadrantes
    

    def __init__(self, dist_matrix, rutas_matrix, entregas):
        """
        Parámetros:
          dist_matrix  : dist[i][j], i=0 es la base
          rutas_matrix : rutas[i][j] = lista de celdas
          entregas     : lista de objetos Entrega (en orden estable)
        """
        self.dist   = dist_matrix
        self.rutas  = rutas_matrix
        self.ent    = entregas       # lista de Entrega
        self.n      = len(entregas)
        self.log    = []             # registro de pasos para mostrar

    # ── Utilidades de distancia ───────────────────────────────────────

    def nodo(self, idx_entrega):
        """Entrega índice → nodo en dist_matrix (base es 0)."""
        return idx_entrega + 1

    def dist_secuencia(self, orden):
        """
        Distancia total de: base → orden[0] → orden[1] → ... → base
        'orden' es una lista de índices de entrega.
        """
        if not orden:
            return 0.0
        total  = self.dist[0][self.nodo(orden[0])]
        for i in range(len(orden) - 1):
            total += self.dist[self.nodo(orden[i])][self.nodo(orden[i+1])]
        total += self.dist[self.nodo(orden[-1])][0]
        return total

    # ── CASO BASE: fuerza bruta ───────────────────────────────────────

    def fuerza_bruta(self, indices, depth):
        """
        Cuando el subproblema es pequeño (≤ UMBRAL_BASE entregas),
        prueba TODAS las permutaciones y elige la de menor distancia.

        Complejidad: O(k!) donde k = len(indices) ≤ UMBRAL_BASE.
        Con UMBRAL_BASE=2 → máximo 2! = 2 permutaciones.

        Este es el CASO BASE del algoritmo recursivo.
        """
        indent = "  " * depth
        if not indices:
            return []
        if len(indices) == 1:
            self.log.append(f"{indent}  [BASE] Solo 1 entrega → {indices}")
            return list(indices)

        mejor_orden = None
        mejor_dist  = float('inf')

        for perm in permutations(indices):
            d = self.dist_secuencia(list(perm))
            if d < mejor_dist:
                mejor_dist  = d
                mejor_orden = list(perm)

        self.log.append(
            f"{indent}  [BASE] {len(indices)} entregas → fuerza bruta → "
            f"orden={mejor_orden} dist={mejor_dist:.1f}"
        )
        return mejor_orden

    # ── DIVIDIR: asignar entregas a cuadrantes ────────────────────────

    def dividir(self, indices, bbox):
        
        # Divide las entregas de 'indices' en 4 cuadrantes según el
        # punto medio del bounding box actual.

        # Cuadrantes (usando (fila, col) de la estación destino):
        #   Q1 = fila ≤ mid_r  AND col ≤ mid_c  (sup-izq)
        #   Q2 = fila ≤ mid_r  AND col >  mid_c  (sup-der)
        #   Q3 = fila >  mid_r AND col ≤ mid_c   (inf-izq)
        #   Q4 = fila >  mid_r AND col >  mid_c  (inf-der)

        # Retorna:
        #   mid_r, mid_c, [q1_indices, q2_indices, q3_indices, q4_indices]
        
        min_r, max_r, min_c, max_c = bbox
        mid_r = (min_r + max_r) // 2
        mid_c = (min_c + max_c) // 2

        q1, q2, q3, q4 = [], [], [], []
        for idx in indices:
            r, c = self.ent[idx].estacion
            if r <= mid_r and c <= mid_c:
                q1.append(idx)
            elif r <= mid_r and c > mid_c:
                q2.append(idx)
            elif r > mid_r and c <= mid_c:
                q3.append(idx)
            else:
                q4.append(idx)

        return mid_r, mid_c, [q1, q2, q3, q4]

    # ── COMBINAR: mejor orden de cuadrantes ──────────────────────────

    def combinar(self, sub_soluciones, depth):
        
        # Dado que cada cuadrante ya tiene su orden interno resuelto,
        # encuentra el MEJOR ORDEN DE VISITA entre los cuadrantes.

        # Prueba todas las permutaciones de grupos (≤4! = 24 casos).
        # Para cada permutación, calcula el costo total:
        #   base → primer cuadrante → segundo → ... → base

        # Este es el paso COMBINAR del algoritmo.

        # El costo entre dos grupos usa:
        #   dist(último del grupo A → primero del grupo B)
        
        indent = "  " * depth
        if len(sub_soluciones) == 1:
            return sub_soluciones[0]

        # Filtrar grupos vacíos
        grupos = [g for g in sub_soluciones if g]

        mejor_flat = None
        mejor_dist = float('inf')

        # Probar todas las formas de ordenar los grupos
        for perm in permutations(range(len(grupos))):
            flat = []
            for i in perm:
                flat.extend(grupos[i])
            d = self.dist_secuencia(flat)
            if d < mejor_dist:
                mejor_dist = d
                mejor_flat = flat[:]

        self.log.append(
            f"{indent}  [COMBINAR] {len(grupos)} grupos → "
            f"mejor orden={mejor_flat} dist={mejor_dist:.1f}"
        )
        return mejor_flat

    # ── RESOLVER: función recursiva principal ─────────────────────────

    def resolver(self, indices, bbox, depth=0):
        
        # Función recursiva de Divide y Vencerás.

        # Parámetros:
        #   indices : índices de entregas a resolver en este nivel
        #   bbox    : (min_r, max_r, min_c, max_c) del cuadrante actual
        #   depth   : profundidad de recursión (para el log)

        # Retorna: lista de índices de entregas en el orden óptimo
        #          para este cuadrante.

        # Árbol de decisión:
        #   len(indices) == 0  → []               (vacío)
        #     len(indices) <= UMBRAL_BASE → brute_force()  CASO BASE
        #   bbox no divisible  → brute_force()    (degeneración)
        #   división no separa → brute_force()    (evitar inf. recursión)
        #   caso general:
        #        mid = punto medio de bbox
        #        Q1..Q4 = dividir por mid
        #        sol_i  = resolver(Qi, sub_bbox_i, depth+1)  CONQUISTA
        #        return combinar([sol_1, sol_2, sol_3, sol_4])  COMBINAR
        
        indent = "  " * depth

        # ── Caso vacío ────────────────────────────────────────────────
        if not indices:
            return []

        # ── Caso base: pocos elementos ────────────────────────────────
        if len(indices) <= UMBRAL_BASE:
            return self.fuerza_bruta(indices, depth)

        min_r, max_r, min_c, max_c = bbox

        # ── Degeneración: bbox de 1 celda o no divisible ──────────────
        if min_r >= max_r and min_c >= max_c:
            self.log.append(f"{indent}  [DEGEN] bbox no divisible → fuerza bruta")
            return self.fuerza_bruta(indices, depth)

        # ── DIVIDIR ───────────────────────────────────────────────────
        mid_r, mid_c, grupos = self.dividir(indices, bbox)

        imprimir_division_cuadrantes(
            # solo mostrar en primeros niveles para no saturar la salida
            [[0]], mid_r, mid_c, grupos, depth
        ) if depth <= 2 else None

        self.log.append(
            f"{indent}[DIV nivel {depth}] {len(indices)} entregas | "
            f"bbox={bbox} | corte=({mid_r},{mid_c}) | "
            f"grupos={[len(g) for g in grupos]}"
        )

        # ── Verificar que la división separa efectivamente ────────────
        # Si todas las entregas caen en el mismo cuadrante, hay riesgo
        # de recursión infinita → resolver con fuerza bruta
        no_vacios = [g for g in grupos if g]
        if len(no_vacios) == 1:
            self.log.append(f"{indent}  [INFO] División no separó → fuerza bruta")
            return self.fuerza_bruta(indices, depth)

        # ── CONQUISTAR: resolver cada cuadrante recursivamente ────────
        bboxes = [
            (min_r,    mid_r, min_c,    mid_c),   # Q1 sup-izq
            (min_r,    mid_r, mid_c+1,  max_c),   # Q2 sup-der
            (mid_r+1,  max_r, min_c,    mid_c),   # Q3 inf-izq
            (mid_r+1,  max_r, mid_c+1,  max_c),   # Q4 inf-der
        ]

        sub_soluciones = []
        for i, (grupo, sub_bbox) in enumerate(zip(grupos, bboxes)):
            if grupo:
                self.log.append(f"{indent}  → Q{i+1}: resolver {grupo} en {sub_bbox}")
                sol = self.resolver(grupo, sub_bbox, depth + 1)
                sub_soluciones.append(sol)

        # ── COMBINAR ──────────────────────────────────────────────────
        resultado = self.combinar(sub_soluciones, depth)
        self.log.append(
            f"{indent}[COMB nivel {depth}] resultado={resultado} "
            f"dist={self.dist_secuencia(resultado):.1f}"
        )
        return resultado

    def ejecutar(self, verbose=True):
        """
        Punto de entrada. Llama a resolver() con todos los índices
        de entregas y el bbox del mapa completo.

        Retorna: (mejor_orden, mejor_distancia)
          mejor_orden: lista de índices de entregas
        """
        if verbose:
            print("\n" + "="*60)
            print("  DIVIDE Y VENCERÁS — Optimización de Rutas")
            print("="*60)
            print(f"  Entregas a resolver : {self.n}")
            print(f"  Umbral caso base    : ≤{UMBRAL_BASE} entregas por cuadrante")
            print("="*60)

        # Las estaciones del mapa definen el bbox inicial
        todos_r = [e.estacion[0] for e in self.ent]
        todos_c = [e.estacion[1] for e in self.ent]
        bbox = (min(todos_r), max(todos_r), min(todos_c), max(todos_c))

        indices = list(range(self.n))
        mejor_orden = self.resolver(indices, bbox, depth=0)
        mejor_dist  = self.dist_secuencia(mejor_orden)

        if verbose:
            print(f"\n  ✓ Orden encontrado  : {mejor_orden}")
            print(f"  ✓ Distancia total   : {mejor_dist:.1f} pasos")

            print("\n" + "─"*60)
            print("  TRAZA COMPLETA DEL ALGORITMO (Divide y Vencerás)")
            print("─"*60)
            for linea in self.log:
                print(f"  {linea}")

        return mejor_orden, mejor_dist



#   4: PRESENTACIÓN DE RESULTADOS


def mostrar_solucion(mejor_orden, entregas, nodos, rutas_matrix, dist_matrix):
    """
    Muestra la solución detallada agrupada por viajes,
    igual que en el módulo del AG para comparar resultados.
    """
    print("\n" + "="*60)
    print("  SOLUCIÓN — DIVIDE Y VENCERÁS")
    print("="*60)

    entregas_ordenadas = [entregas[i] for i in mejor_orden]
    viajes = crear_viajes(entregas_ordenadas)

    ruta_completa   = []
    distancia_total = 0.0
    base            = nodos[0]

    print(f"\n  Base   : {base}")
    print(f"  Viajes : {len(viajes)}")

    for num_viaje, viaje in enumerate(viajes, 1):
        peso_viaje = sum(e.peso for e in viaje)
        print(f"\n{'─'*60}")
        print(f"  VIAJE {num_viaje}  ({len(viaje)} entrega/s | peso: {peso_viaje} kg)")
        print(f"{'─'*60}")

        nodo_actual = 0
        ruta_viaje  = []

        for entrega in viaje:
            nodo_dest = entregas.index(entrega) + 1
            dist      = dist_matrix[nodo_actual][nodo_dest]
            segmento  = rutas_matrix[nodo_actual][nodo_dest]
            distancia_total += dist

            if ruta_viaje:
                ruta_viaje.extend(segmento[1:])
            else:
                ruta_viaje.extend(segmento)

            print(f"\n    → {entrega.id}")
            print(f"      Destino  : {entrega.estacion}")
            print(f"      Peso     : {entrega.peso} kg")
            print(f"      Distancia: {dist:.0f} pasos")
            print(f"      Ruta     : {' → '.join(str(p) for p in segmento)}")
            nodo_actual = nodo_dest

        dist_reg = dist_matrix[nodo_actual][0]
        seg_reg  = rutas_matrix[nodo_actual][0]
        distancia_total += dist_reg
        ruta_viaje.extend(seg_reg[1:])
        ruta_completa.extend(ruta_viaje)

        print(f"\n    Regreso a base : {dist_reg:.0f} pasos")

    print(f"\n{'═'*60}")
    print(f"  DISTANCIA TOTAL (todos los viajes): {distancia_total:.0f} pasos")
    print(f"{'═'*60}")

    return ruta_completa, distancia_total


def imprimir_mapa_simple(matriz, ruta=None, destinos=None):
    """Visualiza el mapa con la ruta resaltada."""
    simbolos = {0: '██', 1: '  ', 2: ' S', 3: ' E'}
    ruta_set  = set(ruta)    if ruta    else set()
    dest_set  = set(destinos) if destinos else set()

    ancho = len(matriz[0]) * 2 + 2
    print(f"\n  [Mapa]  S=Inicio  E=Estación  ░░=Ruta  ██=Pared")
    print(f"  {'─'*ancho}")
    for r, fila in enumerate(matriz):
        print("│ ", end="")
        for c, celda in enumerate(fila):
            pos = (r, c)
            if pos in dest_set:
                print("◉◉", end="")
            elif pos in ruta_set:
                print("░░", end="")
            else:
                print(simbolos.get(celda, '??'), end="")
        print(" │")
    print(f"  {'─'*ancho}")



#   5: INSTRUCCIONES PARA EL ROBOT


def ruta_a_instrucciones(ruta, puntos_entrega):
    """
    Convierte la ruta en comandos simples para el robot.
    FORWARD N, LEFT, RIGHT, DELIVER, STOP.
    El robot inicia mirando al SUR (1,0).
    """
    if len(ruta) < 2:
        return ["STOP"]

    puntos_set    = set(puntos_entrega)
    instrucciones = []
    direccion     = (1, 0)

    def giro_izq(d): return (-d[1],  d[0])
    def giro_der(d): return ( d[1], -d[0])

    pendientes = 0

    def vaciar():
        nonlocal pendientes
        if pendientes > 0:
            instrucciones.append(f"FORWARD {pendientes}")
            pendientes = 0

    for i in range(1, len(ruta)):
        dr = ruta[i][0] - ruta[i-1][0]
        dc = ruta[i][1] - ruta[i-1][1]
        req = (dr, dc)

        if req == direccion:
            pendientes += 1
        elif req == giro_izq(direccion):
            vaciar(); instrucciones.append("LEFT")
            pendientes += 1; direccion = giro_izq(direccion)
        elif req == giro_der(direccion):
            vaciar(); instrucciones.append("RIGHT")
            pendientes += 1; direccion = giro_der(direccion)
        else:
            vaciar(); instrucciones.append("RIGHT"); instrucciones.append("RIGHT")
            pendientes += 1; direccion = giro_der(giro_der(direccion))

        if ruta[i] in puntos_set:
            vaciar(); instrucciones.append("DELIVER")

    vaciar()
    instrucciones.append("STOP")
    return instrucciones


def mostrar_instrucciones(instrucciones):
    print("\n" + "="*60)
    print("  INSTRUCCIONES PARA EL ROBOT")
    print("="*60)
    for i, inst in enumerate(instrucciones, 1):
        print(f"  {i:3d}. {inst}")
    print(f"\n  Total: {len(instrucciones)} instrucciones")



#   6: FUNCIÓN PÚBLICA DE INTEGRACIÓN


def ejecutar_divide_y_venceras(matriz, inicio, estaciones,
                                entregas_validadas, verbose=True):
   
    # Parámetros:
    #   matriz             : misma matriz que construye el proyecto
    #   inicio             : tupla (fila, col) del inicio del robot
    #   estaciones         : lista de tuplas de estaciones del mapa
    #   entregas_validadas : lista de objetos Entrega ya validados

    # Retorna: (mejor_orden, distancia_total, ruta_completa, instrucciones)
    
    if not entregas_validadas:
        print("[ERROR] No hay entregas.")
        return None, None, None, None

    # Filtrar destinos no alcanzables
    alcanzables = _alcanzables(matriz, inicio)
    entregas_ok = []
    for e in entregas_validadas:
        if e.estacion in alcanzables:
            entregas_ok.append(e)
        else:
            print(f"  [AVISO] {e.id} descartada: {e.estacion} no alcanzable.")

    if not entregas_ok:
        print("[ERROR] Ningún destino es alcanzable.")
        return None, None, None, None

    # Nodo 0 = base, nodos 1..n = estaciones de las entregas
    nodos = [inicio] + [e.estacion for e in entregas_ok]

    print(f"\n[DYV] Nodos del grafo:")
    print(f"  Nodo 0 (Base): {inicio}")
    for i, e in enumerate(entregas_ok, 1):
        print(f"  Nodo {i} ({e.id}): {e.estacion}")

    # Construir matrices de distancia y rutas con BFS
    dist_matrix, rutas_matrix = construir_matrices(matriz, nodos)

    # Ejecutar Divide y Vencerás
    dyv = DivideYVenceras(dist_matrix, rutas_matrix, entregas_ok)
    mejor_orden, mejor_dist = dyv.ejecutar(verbose=verbose)

    # Mostrar solución y mapa
    ruta_completa, dist_total = mostrar_solucion(
        mejor_orden, entregas_ok, nodos, rutas_matrix, dist_matrix
    )

    destinos = [e.estacion for e in entregas_ok]
    imprimir_mapa_simple(matriz, ruta=ruta_completa, destinos=destinos)

    # Instrucciones para el robot
    instrucciones = ruta_a_instrucciones(ruta_completa, destinos)
    mostrar_instrucciones(instrucciones)

    # Guardar resultados
    resultado = {
        "algoritmo"      : "Divide y Vencerás",
        "mejor_orden"    : [entregas_ok[i].id for i in mejor_orden],
        "distancia_total": dist_total,
        "instrucciones"  : instrucciones,
        "traza"          : dyv.log
    }
    with open("resultado_dyv.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print("\n[OK] Resultados guardados en resultado_dyv.json")

    return mejor_orden, dist_total, ruta_completa, instrucciones



#   7: STANDALONE (ejecutar solo)


if __name__ == "__main__":
    print("\n" + "█"*60)
    print("  SMART DELIVERY ROBOT — Divide y Vencerás (standalone)")
    print("█"*60)

    json_path = input("\nRuta al JSON del mapa (Enter = prueba.json): ").strip()
    if not json_path:
        json_path = "prueba.json"

    matriz, inicio, estaciones = cargar_mapa(json_path)
    print(f"\nInicio    : {inicio}")
    print(f"Estaciones: {estaciones}")

    print("\n[ENTREGAS] Generando entregas de ejemplo...")
    random.seed(7)
    entregas_raw = []
    for i, est in enumerate(estaciones[:6]):
        peso = random.randint(1, 10)
        entregas_raw.append(Entrega(f"Encargo: {i+1}", peso, est))

    entregas_validas = validar_entregas(entregas_raw, estaciones)
    print(f"\nEntregas ({len(entregas_validas)}):")
    for e in entregas_validas:
        print(f"  {e}")

    ejecutar_divide_y_venceras(matriz, inicio, estaciones, entregas_validas)