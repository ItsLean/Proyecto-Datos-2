class Entrega:

    def __init__(self, identificacion, peso, estacion):

        self.id = identificacion
        self.peso = peso
        self.estacion = estacion

    def __str__(self):

        return f"{self.id} | Peso: {self.peso}kg | Destino: {self.estacion}"


def validar_entregas(entregas, estaciones):

    entregas_validas = []

    for entrega in entregas:

        if entrega.estacion not in estaciones:

            print(f"ERROR: {entrega.id} tiene estación inválida")
            continue

        if entrega.peso > 20:

            print(f"ERROR: {entrega.id} excede el peso máximo")
            continue

        entregas_validas.append(entrega)

    return entregas_validas