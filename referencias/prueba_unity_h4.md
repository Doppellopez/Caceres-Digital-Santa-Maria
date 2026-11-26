# Prueba temprana en Unity (H4 parcial, 2026-11-25)

Pedida por Jorge tras aprobar H1. Unity 6000.3.6f1 y URP 17.3.0 (las versiones de Qazrix), en un proyecto vacío fuera de Qazrix: `%USERPROFILE%\CaceresDigital_PruebaUnity`, escena `Assets/SantaMaria/Prueba.unity`. Ejecución en modo por lotes; nadie lo ha recorrido a mano.

## Reproducir

```
blender -b --factory-startup -P herramientas/h4_exportar_unity.py
powershell -File herramientas/h4_probar_unity.ps1
```

Salida: `exports/unity/` (FBX, texturas, `manifiesto.json`) y `renders/h4_unity/` (capturas e `informe_unity.txt`).

## Resultados

| Comprobación | Resultado |
|---|---|
| Mallas y triángulos | 144 de 144; 82.784 de 82.784 |
| Escala y ejes | 5 objetos de control, error 0 m (X este, Y arriba, Z norte) |
| Materiales | 144 objetos asignados por nombre; textura y normales de la sillería cargadas |
| Normales del relieve | Se ven coherentes a ojo; no medido |
| Figura de 1,80 m | Puertas de unos 4,2 m, proporción verosímil con la foto |
| Terreno en la plaza | 3.721 puntos, ninguno sin suelo |
| Recorridos (cápsula 1,80 m, radio 0,3, peldaño 0,3) | De la plaza a la puerta subiendo las escaleras y 23 m a lo largo de la fachada: completados |
| Caras invisibles, vistas peatonales y portada | 0 % |

## Problemas

- **Cubiertas de la concatedral invisibles desde arriba.** `Concatedral_nave`, `_ala_norte`, `_ala_sur` y `_abside` (v0.3, unos 900 m²) tienen todas las normales hacia abajo. Blender las dibuja por ambas caras y por eso no se detectó antes, tampoco en la revisión de H1. Las 33 cubiertas de los demás edificios, la de la torre y el cierre de H1 miran hacia arriba. **Sin corregir: pendiente de Jorge** (cambia el maestro aprobado, sin mover vértices).
- En la vista general, un 7,3 % de los rayos da en caras vistas por detrás: 1.352 en la concatedral y el resto en otros edificios, sin determinar si son normales invertidas o huecos.
- La exportación necesita girar 180° la copia antes de escribir el FBX; cambiar el eje frontal del exportador no tuvo efecto.
- La primera captura en modo por lotes salía con materiales en blanco por la compilación de shaders; el script la desactiva.

## No probado

Modo Play, personaje y cámara de Qazrix, rendimiento, LOD, colisiones simplificadas (se usan `MeshCollider` sobre las 144 mallas), compilaciones y materiales definitivos de lo provisional (color plano). La iluminación es la de la prueba, no forma parte del entregable.
