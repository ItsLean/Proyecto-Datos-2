PESO_MAXIMO = 20
MAX_DELIVERIES_PER_TRIP = 2


def crear_viajes(entregas):

    viajes = []

    viaje_actual = []

    peso_actual = 0

    for entrega in entregas:

        if (
            peso_actual + entrega.peso <= PESO_MAXIMO
            and len(viaje_actual) < MAX_DELIVERIES_PER_TRIP
        ):

            viaje_actual.append(entrega)

            peso_actual += entrega.peso

        else:

            viajes.append(viaje_actual)

            viaje_actual = [entrega]

            peso_actual = entrega.peso

    if viaje_actual:
        viajes.append(viaje_actual)

    return viajes