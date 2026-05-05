

import json
import random
import os
from collections import deque

from Entregas import Entrega, validar_entregas
from Viajes import crear_viajes, PESO_MAXIMO, MAX_DELIVERIES_PER_TRIP


#Carga del mapilla

# Conversión de texto - número 
VALORES = {
    "Camino":   1,
    "Inicio":   2,
    "Estacion": 3
}


def cargar_mapa(json_path="prueba.json"):
    
   # Lee el JSON con el formato del proyecto
   # Se construye la matriz
   # Retorna: (matriz, inicio, estaciones)
    
    with open(json_path) as f:
        data = json.load(f)

    max_fila = max(item["fila"] for item in data)
    max_col  = max(item["columna"] for item in data)

    # Matriz de ceros (0 = no transitable)
    matriz = [[0] * max_col for _ in range(max_fila)]

    for item in data:
        f = item["fila"] - 1       # JSON usa índice 1, Python usa índice 0
        c = item["columna"] - 1
        matriz[f][c] = VALORES.get(item["valor"], 0)

    # Buscar inicio (tipo 2) y estaciones (tipo 3)
    inicio     = None
    estaciones = []

    for i in range(len(matriz)):
        for j in range(len(matriz[0])):
            if matriz[i][j] == 2:
                inicio = (i, j)
            elif matriz[i][j] == 3:
                estaciones.append((i, j))

    return matriz, inicio, estaciones


def imprimir_mapa(matriz, ruta=None, destinos=None):
    """
    Visualiza la matriz en consola.
      ' S' = Inicio,  ' E' = Estación
      '░░' = celda en la ruta óptima
      '██' = pared/obstáculo
    """
    simbolos = {0: '██', 1: '  ', 2: ' S', 3: ' E'}
    ruta_set    = set(ruta)    if ruta    else set()
    destino_set = set(destinos) if destinos else set()

    ancho = len(matriz[0]) * 2 + 2
    print("\n  [Mapa]  S=Inicio  E=Estación  ░░=Ruta  ██=Pared")
    print("  " + "─" * ancho)
    for r, fila in enumerate(matriz):
        print("│ ", end="")
        for c, celda in enumerate(fila):
            pos = (r, c)
            if pos in destino_set:
                print("◉◉", end="")
            elif pos in ruta_set:
                print("░░", end="")
            else:
                print(simbolos.get(celda, '??'), end="")
        print(" │")
    print("  " + "─" * ancho)



#  BFS — igual que en Proyecto_2_Datos_2.py
#  pero encapsulado para recibir la matriz

def bfs(matriz, inicio, objetivo):
    """
    BFS para encontrar la ruta más corta entre dos celdas.
    Misma lógica que en Proyecto_2_Datos_2.py, pero recibe
    la matriz como parámetro en lugar de usar una global.

    Retorna: lista de celdas (camino), o None si no existe ruta.
    La distancia es len(camino) - 1.
    """
    movimientos = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    filas = len(matriz)
    cols  = len(matriz[0])

    visitado = [[False] * cols for _ in range(filas)]
    padre    = [[None]  * cols for _ in range(filas)]

    cola = deque([inicio])
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

    # Reconstruir camino desde objetivo hasta inicio
    camino  = []
    actual  = objetivo
    while actual:
        camino.append(actual)
        actual = padre[actual[0]][actual[1]]
    camino.reverse()

    if camino and camino[0] == inicio:
        return camino
    return None  # No hay ruta


def construir_matriz_distancias(matriz, nodos):
    """
    Calcula distancias y rutas entre todos los pares de nodos
    usando BFS. Los nodos son: [inicio] + [estacion_de_cada_entrega].

    Complejidad: O(N² *filas * cols)

    Retorna:
      dist[i][j]  = distancia (pasos) del nodo i al nodo j
      rutas[i][j] = lista de celdas del nodo i al nodo j
    """
    n = len(nodos)
    dist  = [[0.0] * n for _ in range(n)]
    rutas = [[[] for _ in range(n)] for _ in range(n)]

    print("\n[BFS] Calculando distancias entre nodos...", end="")
    for i in range(n):
        for j in range(n):
            if i != j:
                camino = bfs(matriz, nodos[i], nodos[j])
                if camino:
                    dist[i][j]  = len(camino) - 1
                    rutas[i][j] = camino
                else:
                    dist[i][j]  = float('inf')
                    rutas[i][j] = []
    print(" listo.")
    return dist, rutas



#  Seccion 3: ALGORITMO GENÉTICO


"""
CÓMO EL AG INTERACTÚA CON crear_viajes():

  Para calcular el fitness:
    1. Se reordena la lista de entregas según esa permutación.
    2. Se llama a crear_viajes(),  agrupa respetando peso y límite.
    3. Se calcula distancia total: para cada viaje, base-est1-...-base.

  El AG busca la permutación que minimiza esa distancia total.

  Se optimiza el orden antes de agrupar pq diay crear_viajes() es greedy: agrupa en orden de llegada.
  Si las entregas cercanas entre sí quedan juntas en la lista,
  crear_viajes() las va a poner en el mismo viaje q seria rutas más cortas.
"""


class AlgoritmoGenetico:

    def __init__(self, dist_matrix, entregas_seleccionadas,
                 pop_size=150, generations=400,
                 mutation_rate=0.05, elite_size=15, tournament_k=5):
        """
        Parámetros:
          dist_matrix            : matriz de distancias (nodo 0 = base)
          entregas_seleccionadas : lista de objetos Entrega ya validados
          pop_size               : tamaño de la población
          generations            : número de generaciones
          mutation_rate          : probabilidad de mutación (0 a 1)
          elite_size             : individuos que pasan sin cambios
          tournament_k           : participantes por torneo
        """
        self.dist      = dist_matrix
        self.entregas  = entregas_seleccionadas
        self.n         = len(entregas_seleccionadas)

        self.pop_size      = pop_size
        self.generations   = generations
        self.mutation_rate = mutation_rate
        self.elite_size    = elite_size
        self.tournament_k  = tournament_k

        # Historial para gráfica de convergencia
        self.historial_mejor   = []
        self.historial_promedio = []
        self.mejor_individuo   = None
        self.mejor_distancia   = float('inf')

    # ── 3.1 POBLACIÓN INICIAL ─────────────────────────────────────────

    def crear_individuo(self):
        """
        Permutación aleatoria de índices [0 .. n-1].
        Cada índice representa una entrega en self.entregas.
        """
        ind = list(range(self.n))
        random.shuffle(ind)
        return ind

    def crear_poblacion(self):
        """Crea pop_size individuos aleatorios."""
        return [self.crear_individuo() for _ in range(self.pop_size)]

    # ── 3.2 FITNESS ───────────────────────────────────────────────────

    def fitness(self, individuo):
        """
        Calcula la distancia total de TODOS los viajes para la
        secuencia de entregas dada por 'individuo'.

        Pasos:
          1. Reordenar entregas según el individuo.
          2. Crear viajes con crear_viajes() (respeta peso y límite).
          3. Para cada viaje: base - estación1 - estación2 - base.
          4. Sumar distancias de todos los viajes.

        Los índices en dist_matrix:
          0         = base (inicio)
          1, 2, ... = estaciones en el orden de self.entregas

        Retorna: distancia total (float). MENOR = MEJOR.
        """
        # Reordenar entregas según el individuo
        entregas_ordenadas = [self.entregas[i] for i in individuo]

        # Crear viajes respetando peso y MAX_DELIVERIES_PER_TRIP
        viajes = crear_viajes(entregas_ordenadas)

        distancia_total = 0.0

        for viaje in viajes:
            nodo_actual = 0  # Base = índice 0 en la dist_matrix

            for entrega in viaje:
                # El índice del nodo de esta entrega en la dist_matrix
                # es su posición en self.entregas + 1 (porque 0 = base)
                nodo_destino = self.entregas.index(entrega) + 1
                distancia_total += self.dist[nodo_actual][nodo_destino]
                nodo_actual = nodo_destino

            # Regresar a la base al final de cada viaje
            distancia_total += self.dist[nodo_actual][0]

        return distancia_total

    def evaluar_poblacion(self, poblacion):
        """
        Evalúa todos los individuos.
        Retorna lista de (fitness, individuo) ordenada de menor a mayor.
        """
        evaluada = [(self.fitness(ind), ind) for ind in poblacion]
        evaluada.sort(key=lambda x: x[0])
        return evaluada

    # ── 3.3 SELECCIÓN POR TORNEO ──────────────────────────────────────

    def seleccion_torneo(self, poblacion_evaluada):
        """
        Elige tournament_k individuos al azar y retorna el de menor fitness.

        Ventaja: robusto ante grandes diferencias de fitness entre
        individuos, más justo que la ruleta cuando hay outliers.
        """
        candidatos = random.sample(poblacion_evaluada, self.tournament_k)
        ganador = min(candidatos, key=lambda x: x[0])
        return ganador[1]

    # ── 3.4 CRUCE OX (ORDER CROSSOVER) ───────────────────────────────

    def cruce_ox(self, padre1, padre2):
        """
        Order Crossover (OX): combina dos padres preservando el orden
        relativo de los genes — ideal para problemas de permutación.

        Algoritmo:
          1. Copiar un segmento aleatorio de padre1 al hijo.
          2. Completar con los genes de padre2 en orden,
             saltando los que ya están en el hijo.

        Ejemplo:
          padre1 = [3, 1, 2, 0, 4]  segmento pos[1..3] = [1,2,0]
          padre2 = [0, 3, 4, 1, 2]
          hijo   = [3, 1, 2, 0, 4]   genes faltantes del padre2: 3,4
        """
        n = len(padre1)
        corte1 = random.randint(0, n - 2)
        corte2 = random.randint(corte1 + 1, n - 1)

        hijo = [None] * n
        hijo[corte1:corte2 + 1] = padre1[corte1:corte2 + 1]
        genes_en_hijo = set(hijo[corte1:corte2 + 1])

        pos_llenar = (corte2 + 1) % n
        pos_padre2 = (corte2 + 1) % n
        faltan     = n - (corte2 - corte1 + 1)
        llenados   = 0

        while llenados < faltan:
            gen = padre2[pos_padre2]
            if gen not in genes_en_hijo:
                hijo[pos_llenar] = gen
                genes_en_hijo.add(gen)
                pos_llenar = (pos_llenar + 1) % n
                llenados  += 1
            pos_padre2 = (pos_padre2 + 1) % n

        return hijo

    # ── 3.5 MUTACIÓN POR SWAP ─────────────────────────────────────────

    def mutacion_swap(self, individuo, tasa=None):
        """
        Con probabilidad 'tasa' (o self.mutation_rate), intercambia
        dos genes al azar. Mantiene la permutación válida.

        Se muta pq evita convergencia prematura a óptimos locales introduciendo
        pequeñas variaciones aleatorias en la población.
        """
        tasa = tasa if tasa is not None else self.mutation_rate
        ind = individuo[:]
        if random.random() < tasa:
            i, j = random.sample(range(len(ind)), 2)
            ind[i], ind[j] = ind[j], ind[i]
        return ind

    # ── 3.6 BUCLE PRINCIPAL ───────────────────────────────────────────

    def ejecutar(self, verbose=True):
        """
        Corre el AG por self.generations generaciones.

        Por cada generación:
          1. Evaluar población.
          2. Elitismo: los mejores pasan intactos.
          3. Reproducción: torneo - cruce OX - mutación swap.
          4. Anti-estancamiento: aumenta mutación si no mejora en 50 gens.

        Retorna: (mejor_individuo, mejor_distancia)
        """
        if verbose:
            print("\n" + "=" * 60)
            print("  ALGORITMO GENÉTICO — Optimización de Rutas")
            print("=" * 60)
            print(f"  Entregas a ordenar : {self.n}")
            print(f"  Población          : {self.pop_size}")
            print(f"  Generaciones       : {self.generations}")
            print(f"  Tasa de mutación   : {self.mutation_rate * 100:.0f}%")
            print(f"  Elitismo           : {self.elite_size} individuos")
            print(f"  Torneo K           : {self.tournament_k}")
            print("=" * 60)

        poblacion          = self.crear_poblacion()
        estancamiento      = 0
        mejor_prev         = float('inf')

        for gen in range(self.generations):

            # ── Evaluar ───────────────────────────────────────────────
            evaluada = self.evaluar_poblacion(poblacion)

            mejor_actual = evaluada[0][0]
            ind_actual   = evaluada[0][1]
            promedio     = sum(e[0] for e in evaluada) / len(evaluada)

            self.historial_mejor.append(mejor_actual)
            self.historial_promedio.append(promedio)

            if mejor_actual < self.mejor_distancia:
                self.mejor_distancia = mejor_actual
                self.mejor_individuo = ind_actual[:]

            # ── Detectar estancamiento ────────────────────────────────
            if abs(mejor_actual - mejor_prev) < 0.001:
                estancamiento += 1
            else:
                estancamiento = 0
            mejor_prev = mejor_actual

            # Si lleva 50 generaciones sin mejorar, triplicar mutación
            tasa_efectiva = self.mutation_rate
            if estancamiento > 50:
                tasa_efectiva = min(0.3, self.mutation_rate * 3)

            if verbose and (gen % 50 == 0 or gen == self.generations - 1):
                print(f"  Gen {gen:4d} | Mejor: {mejor_actual:.1f} | "
                      f"Prom: {promedio:.1f} | Estancado: {estancamiento}")

            # ── Nueva generación ──────────────────────────────────────
            # Elitismo: los mejores pasan directos
            nueva_pob = [ind for (_, ind) in evaluada[:self.elite_size]]

            while len(nueva_pob) < self.pop_size:
                padre1 = self.seleccion_torneo(evaluada)
                padre2 = self.seleccion_torneo(evaluada)
                hijo   = self.cruce_ox(padre1, padre2)
                hijo   = self.mutacion_swap(hijo, tasa_efectiva)
                nueva_pob.append(hijo)

            poblacion = nueva_pob

        if verbose:
            print(f"\n  ✓ Mejor distancia total encontrada: {self.mejor_distancia:.1f} pasos")

        return self.mejor_individuo, self.mejor_distancia



#  Seccion 4: PRESENTACIÓN DE RESULTADOS


def mostrar_solucion(mejor_orden, entregas, nodos, rutas_matrix, dist_matrix):
    """
    Muestra la solución detallada agrupada por viajes.

    Parámetros:
      mejor_orden  : permutación óptima de índices de entregas
      entregas     : lista original de objetos Entrega
      nodos        : [inicio] + [estacion_de_cada_entrega]
      rutas_matrix : rutas_matrix[i][j] = lista de celdas
      dist_matrix  : dist_matrix[i][j] = distancia
    """
    print("\n" + "=" * 60)
    print("  SOLUCIÓN — ALGORITMO GENÉTICO")
    print("=" * 60)

    # Reordenar entregas según la mejor permutación encontrada
    entregas_ordenadas = [entregas[i] for i in mejor_orden]
    viajes = crear_viajes(entregas_ordenadas)

    ruta_completa  = []
    distancia_total = 0.0
    base = nodos[0]

    print(f"\n  Base: {base}")
    print(f"  Viajes generados: {len(viajes)}")

    for num_viaje, viaje in enumerate(viajes, 1):
        print(f"\n{'─'*60}")
        print(f"  VIAJE {num_viaje}  ({len(viaje)} entrega/s, "
              f"peso total: {sum(e.peso for e in viaje)} kg)")
        print(f"{'─'*60}")

        nodo_actual = 0  # Base
        ruta_viaje  = []

        for entrega in viaje:
            nodo_destino = entregas.index(entrega) + 1
            dist         = dist_matrix[nodo_actual][nodo_destino]
            segmento     = rutas_matrix[nodo_actual][nodo_destino]

            distancia_total += dist
            if ruta_viaje:
                ruta_viaje.extend(segmento[1:])   # evitar duplicar nodo
            else:
                ruta_viaje.extend(segmento)

            print(f"\n    - Entrega : {entrega.id}")
            print(f"      Destino  : {entrega.estacion}")
            print(f"      Peso     : {entrega.peso} kg")
            print(f"      Distancia: {dist:.0f} pasos")
            print(f"      Ruta     : {' - '.join(str(p) for p in segmento)}")

            nodo_actual = nodo_destino

        # Regreso a la base
        dist_regreso    = dist_matrix[nodo_actual][0]
        segmento_regreso = rutas_matrix[nodo_actual][0]
        distancia_total += dist_regreso
        ruta_viaje.extend(segmento_regreso[1:])

        print(f"\n    Regreso a base: {dist_regreso:.0f} pasos")
        ruta_completa.extend(ruta_viaje)

    print(f"\n{'═'*60}")
    print(f"  DISTANCIA TOTAL (todos los viajes): {distancia_total:.0f} pasos")
    print(f"{'═'*60}")

    return ruta_completa, distancia_total


def mostrar_convergencia(historial_mejor, historial_promedio):
    """
    Gráfica ASCII de convergencia del algoritmo genético.

    Lo que muestra:
      ● = mejor individuo de cada generación
      ○ = promedio de la población

    Una buena convergencia:
      - El mejor (●) cae rápido en las primeras generaciones (exploración).
      - Luego se estabiliza (explotación del óptimo encontrado).
      - El promedio (○) converge hacia el mejor con el tiempo.
    """
    print("\n" + "=" * 60)
    print("  CONVERGENCIA DEL ALGORITMO GENÉTICO")
    print("=" * 60)

    if not historial_mejor:
        return

    n      = len(historial_mejor)
    paso   = max(1, n // 20)
    muestra_mejor = historial_mejor[::paso]
    muestra_prom  = historial_promedio[::paso]

    min_val = min(muestra_mejor)
    max_val = max(muestra_prom)
    alto    = 10
    ancho   = len(muestra_mejor)

    def normalizar(val):
        if max_val == min_val:
            return alto // 2
        return int((max_val - val) / (max_val - min_val) * alto)

    grafica = [[' '] * (ancho + 8) for _ in range(alto + 2)]

    for col, (b, a) in enumerate(zip(muestra_mejor, muestra_prom)):
        rb = normalizar(b)
        ra = normalizar(a)
        if 0 <= rb <= alto:
            grafica[rb][col + 7] = '●'
        if 0 <= ra <= alto:
            grafica[ra][col + 7] = '○'

    print(f"  Dist")
    for fila_idx, fila in enumerate(grafica):
        if fila_idx == 0:
            etiqueta = f"  {max_val:6.0f} │"
        elif fila_idx == alto:
            etiqueta = f"  {min_val:6.0f} │"
        elif fila_idx % 2 == 0:
            val = max_val - (fila_idx / alto) * (max_val - min_val)
            etiqueta = f"  {val:6.0f} │"
        else:
            etiqueta = f"         │"
        print(etiqueta + ''.join(fila))

    print(f"         └" + "─" * (ancho + 4))
    print(f"          Gen 1{' ' * (ancho - 8)}Gen {n}")
    print(f"\n  ● = Mejor individuo   ○ = Promedio de población")

    if historial_mejor[0] > 0:
        mejora = (1 - historial_mejor[-1] / historial_mejor[0]) * 100
        print(f"\n  Interpretación:")
        print(f"    • Generación 1  - distancia inicial: {historial_mejor[0]:.1f}")
        print(f"    • Generación {n} - distancia final:   {historial_mejor[-1]:.1f}")
        print(f"    • Mejora lograda: {mejora:.1f}%")
        print(f"    • La caída al inicio = exploración del espacio de búsqueda.")
        print(f"    • La estabilización  = convergencia hacia el óptimo local.")

#Para ver grafica de convergencia del algoritmo genetico 
import matplotlib.pyplot as plt

def guardar_grafica_convergencia(historial_mejor, historial_promedio):
    generaciones = list(range(1, len(historial_mejor) + 1))
    
    plt.figure(figsize=(10, 5))
    plt.plot(generaciones, historial_mejor,   label="Mejor individuo",      color="blue")
    plt.plot(generaciones, historial_promedio, label="Promedio población",   color="orange", linestyle="--")
    
    plt.title("Convergencia del Algoritmo Genético")
    plt.xlabel("Generación")
    plt.ylabel("Distancia total (pasos)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("convergencia_ag.png", dpi=150)
    plt.show()
    print("[OK] Gráfica guardada en convergencia_ag.png")

#  Seccion 5: INSTRUCCIONES PARA EL ROBOT


def ruta_a_instrucciones(ruta_completa, puntos_entrega):
    """
    Convierte la ruta completa en comandos simples para el robot.
    Inserta DELIVER cuando el robot llega a una estación de entrega.

    Comandos generados:
      FORWARD N  = avanzar N celdas
      LEFT       = girar 90° izquierda
      RIGHT      = girar 90° derecha
      DELIVER    = realizar entrega
      STOP       = fin del recorrido

    El robot inicia mirando hacia el SUR (dirección (1,0)).
    """
    if len(ruta_completa) < 2:
        return ["STOP"]

    puntos_set   = set(puntos_entrega)
    instrucciones = []
    direccion     = (1, 0)  # Sur

    def girar_izq(d):  return (-d[1],  d[0])
    def girar_der(d):  return ( d[1], -d[0])

    forwards_pendientes = 0

    def vaciar_forwards():
        nonlocal forwards_pendientes
        if forwards_pendientes > 0:
            instrucciones.append(f"FORWARD {forwards_pendientes}")
            forwards_pendientes = 0

    for i in range(1, len(ruta_completa)):
        dr = ruta_completa[i][0] - ruta_completa[i-1][0]
        dc = ruta_completa[i][1] - ruta_completa[i-1][1]
        requerido = (dr, dc)

        if requerido == direccion:
            forwards_pendientes += 1
        elif requerido == girar_izq(direccion):
            vaciar_forwards()
            instrucciones.append("LEFT")
            forwards_pendientes += 1
            direccion = girar_izq(direccion)
        elif requerido == girar_der(direccion):
            vaciar_forwards()
            instrucciones.append("RIGHT")
            forwards_pendientes += 1
            direccion = girar_der(direccion)
        else:
            # U-turn (180°)
            vaciar_forwards()
            instrucciones.append("RIGHT")
            instrucciones.append("RIGHT")
            forwards_pendientes += 1
            direccion = girar_der(girar_der(direccion))

        # ¿Llegamos a un punto de entrega?
        if ruta_completa[i] in puntos_set:
            vaciar_forwards()
            instrucciones.append("DELIVER")

    vaciar_forwards()
    instrucciones.append("STOP")
    return instrucciones


def mostrar_instrucciones(instrucciones):
    """Imprime la secuencia de instrucciones numerada."""
    print("\n" + "=" * 60)
    print("  INSTRUCCIONES PARA EL ROBOT")
    print("=" * 60)
    for i, inst in enumerate(instrucciones, 1):
        print(f"  {i:3d}. {inst}")
    print(f"\n  Total: {len(instrucciones)} instrucciones")



#  Seccion 6: MAIN


def _estaciones_alcanzables(matriz, inicio):
    """
    BFS desde el inicio para determinar qué celdas son alcanzables.
    Retorna un set de tuplas (fila, col) alcanzables.
    """
    visitado = set()
    cola = deque([inicio])
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


def ejecutar_algoritmo_genetico(matriz, inicio, estaciones, entregas_validadas,
                                 pop_size=150, generations=400,
                                 mutation_rate=0.05, elite_size=15,
                                 tournament_k=5, verbose=True):
    """
    Función principal del módulo. Sellama desde Proyecto_2_Datos_2.py.

    Parámetros:
      matriz             : la misma matriz que construye el proyecto
      inicio             : tupla (fila, col) del inicio del robot
      estaciones         : lista de tuplas de estaciones
      entregas_validadas : lista de objetos Entrega ya validados

    Retorna:
      (mejor_orden, mejor_distancia, ruta_completa, instrucciones)
    """
    if not entregas_validadas:
        print("[ERROR] No hay entregas para optimizar.")
        return None, None, None, None

    # Filtrar entregas cuyo destino no es alcanzable desde la base
    # (puede ocurrir si el mapa tiene estaciones en callejones sin salida)
    alcanzables = _estaciones_alcanzables(matriz, inicio)
    entregas_alcanzables = []
    for e in entregas_validadas:
        if e.estacion in alcanzables:
            entregas_alcanzables.append(e)
        else:
            print(f"  [AVISO] {e.id} descartada: destino {e.estacion} no es alcanzable.")

    if not entregas_alcanzables:
        print("[ERROR] Ninguna entrega tiene destino alcanzable desde la base.")
        return None, None, None, None

    # Nodos: [inicio] + [estacion de cada entrega alcanzable]
    # El índice 0 siempre es la base
    nodos = [inicio] + [e.estacion for e in entregas_alcanzables]

    print(f"\n[AG] Nodos del grafo:")
    print(f"  Nodo 0 (Base): {inicio}")
    for i, e in enumerate(entregas_alcanzables, 1):
        print(f"  Nodo {i} ({e.id}): {e.estacion}")

    # Construir matriz de distancias con BFS
    dist_matrix, rutas_matrix = construir_matriz_distancias(matriz, nodos)

    # Reemplazar entregas_validadas por las alcanzables para el resto del flujo
    entregas_validadas = entregas_alcanzables

    # Ejecutar el Algoritmo Genético
    ag = AlgoritmoGenetico(
        dist_matrix=dist_matrix,
        entregas_seleccionadas=entregas_validadas,
        pop_size=pop_size,
        generations=generations,
        mutation_rate=mutation_rate,
        elite_size=elite_size,
        tournament_k=tournament_k
    )

    mejor_orden, mejor_distancia = ag.ejecutar(verbose=verbose)

    # Mostrar solución detallada
    ruta_completa, dist_total = mostrar_solucion(
        mejor_orden, entregas_validadas, nodos, rutas_matrix, dist_matrix
    )

    # Mapa con la ruta resaltada
    destinos = [e.estacion for e in entregas_validadas]
    imprimir_mapa(matriz, ruta=ruta_completa, destinos=destinos)

    # Gráfica de convergencia
    mostrar_convergencia(ag.historial_mejor, ag.historial_promedio)
    guardar_grafica_convergencia(ag.historial_mejor, ag.historial_promedio)  
    # Instrucciones para el robot
    instrucciones = ruta_a_instrucciones(ruta_completa, destinos)
    mostrar_instrucciones(instrucciones)

    # Guardar resultados en JSON
    resultados = {
        "algoritmo"        : "Algoritmo Genético",
        "mejor_orden"      : [entregas_validadas[i].id for i in mejor_orden],
        "distancia_total"  : dist_total,
        "instrucciones"    : instrucciones,
        "convergencia": {
            "mejor_por_generacion"   : ag.historial_mejor[::10],
            "promedio_por_generacion": ag.historial_promedio[::10]
        }
    }
    with open("resultado_genetico.json", "w") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print("\n[OK] Resultados guardados en resultado_genetico.json")

    return mejor_orden, mejor_distancia, ruta_completa, instrucciones




if __name__ == "__main__":
    print("\n" + "█" * 60)
    print("  SMART DELIVERY ROBOT — Algoritmo Genético (standalone)")
    print("█" * 60)

    # Cargar mapa
    json_path = input("\nRuta al JSON del mapa (Enter = prueba.json): ").strip()
    if not json_path:
        json_path = "prueba.json"

    matriz, inicio, estaciones = cargar_mapa(json_path)

    print(f"\nInicio: {inicio}")
    print(f"Estaciones ({len(estaciones)}): {estaciones}")
    imprimir_mapa(matriz)

    
    print("\n[ENTREGAS] Generando entregas de ejemplo...")
    entregas_raw = []
    for i, est in enumerate(estaciones[:6]):  # máximo 6 entregas
        peso = random.randint(1, 10)
        entregas_raw.append(Entrega(f"Encargo: {i+1}", peso, est))

    # Validar con la función del proyecto
    entregas_validas = validar_entregas(entregas_raw, estaciones)

    print(f"\nEntregas válidas ({len(entregas_validas)}):")
    for e in entregas_validas:
        print(f"  {e}")

    # Ejecutar AG
    ejecutar_algoritmo_genetico(
        matriz=matriz,
        inicio=inicio,
        estaciones=estaciones,
        entregas_validadas=entregas_validas
    )
   