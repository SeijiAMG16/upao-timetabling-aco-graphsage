from proyecciones_loader import ProyeccionesLoader

print("Probando ProyeccionesLoader con Libro1.xlsx...")
loader = ProyeccionesLoader('../inputs/Libro1.xlsx')

print(f"Total proyecciones cargadas: {len(loader.proyecciones)}")
print("\nPrimeras 5 proyecciones:")
for i, (curso, proy) in enumerate(list(loader.proyecciones.items())[:5]):
    print(f"  {curso}: T={proy['teoria']}, P={proy['practica']}, L={proy['laboratorio']}")

print("\nEjemplo de búsqueda:")
ejemplo = loader.obtener_proyeccion("CALCULO I")
if ejemplo:
    print(f"CALCULO I: {ejemplo}")
else:
    print("CALCULO I no encontrado")