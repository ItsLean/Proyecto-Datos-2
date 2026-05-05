import json
from collections import deque
from Entregas import Entrega, validar_entregas
from Viajes import crear_viajes
import random

# Conversión de texto → número
valores = {
    "Camino": 1,
    "Inicio": 2,
    "Estacion": 3
}

# Leer JSON
with open("prueba.json") as f:
    data = json.load(f)

# Obtener tamaño del mapa
max_fila = max(item["fila"] for item in data)
max_col = max(item["columna"] for item in data)

# Crear matriz llena de ceros
matriz = [[0 for _ in range(max_col)] for _ in range(max_fila)]

# Llenar la matriz
for item in data:
    f = item["fila"] - 1
    c = item["columna"] - 1
    valor = item["valor"]
    
    matriz[f][c] = valores.get(valor, 0)

print("MATRIZ:")
for fila in matriz:
    print(fila)

# Movimientos posibles
movimientos = [(-1,0),(1,0),(0,-1),(0,1)]

# Encontrar inicio y estaciones
inicio = None
estaciones = []

for i in range(len(matriz)):
    for j in range(len(matriz[0])):
        if matriz[i][j] == 2:
            inicio = (i, j)
        elif matriz[i][j] == 3:
            estaciones.append((i, j))

print("\nInicio:", inicio)
print("Estaciones:", estaciones)


# CREA ENTREGAS
cantidad_entregas = 6

entregas = []

for i in range(cantidad_entregas):

    id_entrega = f"Encargo: {i+1}"

    peso = random.randint(1, 20)

    estacion = random.choice(estaciones)

    nueva_entrega = Entrega(id_entrega, peso, estacion)

    entregas.append(nueva_entrega)

# Validar entregas
entregas = validar_entregas(entregas, estaciones)

print("\nENTREGAS:")

for entrega in entregas:
    print(entrega)


# BFS (ruta más corta)
def bfs(inicio, objetivo):
    filas, cols = len(matriz), len(matriz[0])
    visitado = [[False]*cols for _ in range(filas)]
    padre = [[None]*cols for _ in range(filas)]
    
    cola = deque([inicio])
    visitado[inicio[0]][inicio[1]] = True

    while cola:
        x, y = cola.popleft()
        
        if (x, y) == objetivo:
            break
        
        for dx, dy in movimientos:
            nx, ny = x + dx, y + dy
            
            if 0 <= nx < filas and 0 <= ny < cols:
                if not visitado[nx][ny] and matriz[nx][ny] != 0:
                    visitado[nx][ny] = True
                    padre[nx][ny] = (x, y)
                    cola.append((nx, ny))

    # Reconstruir camino
    camino = []
    actual = objetivo
    
    while actual:
        camino.append(actual)
        actual = padre[actual[0]][actual[1]]
    
    camino.reverse()
    
    if camino and camino[0] == inicio:
        return camino
    return None

# Calcular rutas a todas las estaciones
mejor_ruta = None
menor_distancia = float("inf")

print("\nRUTAS:")

for estacion in estaciones:
    ruta = bfs(inicio, estacion)
    
    if ruta:
        print(f"\nRuta a estación {estacion}:")
        print(ruta)
        print(f"Longitud: {len(ruta)}")
        
        if len(ruta) < menor_distancia:
            menor_distancia = len(ruta)
            mejor_ruta = ruta
    else:
        print(f"No hay ruta a {estacion}")

# Mostrar mejor ruta
if mejor_ruta:
    print("\nMEJOR RUTA:")
    print(mejor_ruta)

    # Marcar ruta en la matriz
    for x, y in mejor_ruta:
        if matriz[x][y] == 1:
            matriz[x][y] = 9

    print("\nMATRIZ CON RUTA (9):")
    for fila in matriz:
        print(fila)
else:
    print("\nNo se encontró ninguna ruta")


# CREAR VIAJES
viajes = crear_viajes(entregas)

print("\nVIAJES:")

for i, viaje in enumerate(viajes, start=1):

    print(f"\nViaje {i}")

    peso_total = 0

    for entrega in viaje:

        print(entrega)

        peso_total += entrega.peso

    print("Peso total:", peso_total)


from AlgoritmoGenetico import ejecutar_algoritmo_genetico
ejecutar_algoritmo_genetico(matriz, inicio, estaciones, entregas)
from Divideyvenceras import ejecutar_divide_y_venceras
ejecutar_divide_y_venceras(matriz, inicio, estaciones, entregas)