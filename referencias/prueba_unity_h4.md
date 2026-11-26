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

## Reexportación con las intervenciones 7 y 8 (2026-11-26)

Pedida por Jorge ("modelo compatible con Unity"). Mismo proyecto vacío y mismos scripts.

- **Paquete para importar:** `exports/unity/SantaMaria.unitypackage` (19 recursos: prefab `SantaMaria.prefab`, FBX, texturas y materiales URP; sin dependencias fuera del paquete). Necesita un proyecto con URP. No incluye ajustes del proyecto ni scripts. No se ha importado en otro proyecto, tampoco en Qazrix.
- 144 de 144 mallas, 83.000 triángulos (tras la intervención 8; 82.784 antes), error de escala y ejes 0 m, materiales asignados a los 144 objetos, ambos recorridos completados.
- Cubiertas v0.3 de la concatedral: sus caras hacia abajo (nave 2, ala norte 16, ala sur 13, ábside 13) se voltean **solo en la exportación**; el maestro sigue sin corregir. En la vista general los rayos que dan en caras vistas por detrás bajan del 7,3 % al 2,7 %; casi todos los restantes son de otros edificios.
- Puerta y medallón se importan sin repetición de textura (`Clamp`).
- Siguen sin probar: modo Play, personaje de Qazrix, rendimiento, LOD y colisiones simplificadas (el prefab lleva un `MeshCollider` por malla).

## Reexportación con la intervención 9, teja (2026-11-26)

- La exportación y el script de Unity admiten varios materiales por malla (cubierta con teja y zona casi plana); se emparejan por nombre.
- 144 de 144 mallas, 83.000 triángulos, error de escala y ejes 0 m, materiales asignados a los 144 objetos, ambos recorridos completados.
- `SantaMaria.unitypackage`: 22 recursos, sin dependencias fuera del paquete.
- En el maestro ya miran hacia arriba ábside y alas; en la exportación solo se voltean las 2 caras de la nave.
- Vista general: 2,7 % de rayos en caras vistas por detrás, como antes.

## Reexportación con la intervención 10 y recorrido a mano (2026-11-26)

- 187 de 187 mallas, 94.226 triángulos, error de escala y ejes 0 m, materiales asignados a los 187 objetos, ambos recorridos completados; paquete de 29 recursos sin dependencias fuera.
- La exportación quita las ranuras de material sin caras.
- `Referencia_180cm` lleva `CharacterController` y `ControlTeclado.cs` (gestor de entrada clásico): W/S o flechas, A/D paso lateral, Q/E giro, Mayús correr, RePág/AvPág mirar, ratón gira la cámara (Esc lo suelta), botón izquierdo foto, V cambia de persona, R vuelve. La cámara va por defecto en los ojos de la figura, que no se ve.
- Comprobado por script, sin modo Play: avance, retroceso y lateral 1,6 m/s, giro, choque contra la portada, giro por ratón (llamando a `Mirar`), foto de 1920 px y vuelta al inicio. **No probado con teclado y ratón reales.**

## Reexportación con la intervención 11, cristalera (2026-11-26)

- 187 de 187 mallas, 187 objetos con material, error de escala y ejes 0 m, recorridos y control por script correctos; paquete de 31 recursos sin dependencias fuera.

## Reexportación con la intervención 12, cristaleras de la nave (2026-11-26)

- 187 de 187 mallas, 187 objetos con material, error de escala y ejes 0 m, recorridos correctos; paquete de 37 recursos sin dependencias fuera.
