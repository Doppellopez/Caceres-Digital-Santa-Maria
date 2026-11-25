# Referencias fotográficas

Registrar aquí URL, autor, licencia, fecha y elemento representado. Los PNG existentes proceden de los modelos y cartografía locales.

## Concatedral, fachada noroeste (Puerta del Evangelio)

Wikimedia Commons, 2026-11-25. Descarga aprobada por Jorge. En `referencias/fotos/` hay tres (SHA-1 igual al publicado por Commons): *Santa María, Cáceres*, *J29 199* y *Concatedral 02*. **Faltan** *West façade* y *exteriores 04*: el servidor limitó las peticiones (HTTP 429).

| Archivo | Autor | Licencia | Fecha de la foto | Píxeles / tamaño | Qué muestra |
|---|---|---|---|---|---|
| [Santa María, Cáceres.JPG](https://commons.wikimedia.org/wiki/File:Santa_Mar%C3%ADa,_C%C3%A1ceres.JPG) | Jesusccastillo | [CC BY-SA 3.0 ES](https://creativecommons.org/licenses/by-sa/3.0/es/) | 2012-01-28 | 4288×2848, 5,26 MB | Fachada casi de frente, portada y torre |
| [J29 199 iglesia de Santa María.jpg](https://commons.wikimedia.org/wiki/File:J29_199_iglesia_de_Santa_Mar%C3%ADa.jpg) | Falk2 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | 2017-06-09 | 4392×3246, 3,47 MB | Portada y torre |
| [Concatedral de Santa María 02.jpg](https://commons.wikimedia.org/wiki/File:Concatedral_de_Santa_Mar%C3%ADa_02.jpg) | Edurne Castillo Prieto | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | 2017-09-16 | 4160×3120, 2,47 MB | Fachada hacia la cabecera |
| [Cáceres Co-Cathedral 2023 - West façade.jpg](https://commons.wikimedia.org/wiki/File:C%C3%A1ceres_Co-Cathedral_2023_-_West_fa%C3%A7ade.jpg) | Fernando (usuario de Commons) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | 2023-10-17 | 3898×3898, 10,89 MB | Esquina de la torre, fachadas oeste y noroeste |
| [Caceres - Catedral, exteriores 04.jpg](https://commons.wikimedia.org/wiki/File:Caceres_-_Catedral,_exteriores_04.jpg) | Zarateman | [CC BY-SA 3.0 ES](https://creativecommons.org/licenses/by-sa/3.0/es/) | 2011-09-15 | 1200×1600, 0,28 MB | Detalle de la portada |

**Aviso de licencia:** CC BY-SA obliga a atribuir y a compartir las obras derivadas con la misma licencia. Se usan para comprobar formas y proporciones. Antes de convertir cualquiera en textura del modelo, Jorge debe decidir si acepta esa obligación; la alternativa son fotos propias o CC0.

`renders/h1_i1_comparacion/foto_con_lineas.png` es obra derivada de *Santa María, Cáceres.JPG* (Jesusccastillo, CC BY-SA 3.0 ES): reducida y con líneas del modelo dibujadas encima. Se comparte con esa misma licencia.

## Textura de prueba

`renders/prueba_piedra*/silleria_*.png` se generan por código (`herramientas/prueba_piedra.py`). No incorporan fotografías. La imagen de sillería que Jorge pegó en el chat (marca de agua de Adobe Stock, n.º 454989721) solo sirvió de referencia visual para la prueba clara: no se guardó ni se usó como textura.

`renders/h1_i2_comparacion/foto_con_lineas.png` es la misma obra derivada tras la intervención 2, con la misma atribución y licencia. Las medidas de contrafuertes y remates se tomaron sobre *Santa María, Cáceres.JPG* y se contrastaron a la vista con *Concatedral de Santa María 02*.

`renders/h1_i3_comparacion/foto_con_lineas.png`: misma obra derivada tras la intervención 3, con la misma atribución y licencia. La portada se midió sobre *Santa María, Cáceres.JPG*.

`renders/h1_i4_comparacion/foto_con_lineas.png`: misma obra derivada tras la intervención 4, con la misma atribución y licencia. *Concatedral de Santa María 02* (Edurne Castillo Prieto, CC BY-SA 4.0) se usó para comprobar a la vista la ventana apuntada.

## Textura del maestro

`texturas/concatedral/silleria_dorada_*.png`: generadas por código (`herramientas/silleria.py`), sin fotografías. El tono se ajustó a ojo mirando las fotos de la concatedral.

## Casco antiguo (ampliación LiDAR, 2026-11-25)

Origen: Centro de Descargas del CNIG/IGN, archivos ya presentes en `../../Research/Source/CNIG` (filas DATA-001 y DATA-002 de `../../Research/ASSET_LICENSES.csv`).

- LiDAR PNOA 2018, cuadro 726-4374, clase 6: cubiertas.
- MDT02 2ª cobertura, hoja 0704-1, ETRS89 HU29: relieve.

Licencia registrada allí: CC BY 4.0, pendiente de confirmar en la ficha de cada producto. Citar origen y propiedad (CNIG/IGN).

`renders/h1_i6_comparacion/foto_con_lineas.png`: misma obra derivada tras la intervención 6, con la misma atribución y licencia. La torre se midió sobre *Santa María, Cáceres.JPG*; la cara noreste se estimó en *J29 199 iglesia de Santa María* (Falk2, CC BY-SA 4.0).

## Red topográfica municipal 2009 (RedPol)

`datos/originales/redpol_2009/`: `RedPol_2009_WEB.dwg`, descargado por Jorge de https://sig.caceres.es/red_pol/red_pol_09/Grafico_de_Red/RedPol_2009_WEB.zip el 2026-11-25. Convertido a DXF con LibreDWG 0.14. Coordenadas en ED50 / UTM 29N. Contiene puntos, visuales y rótulos de la red topográfica; no edificios. Licencia sin comprobar: no publicar ni redistribuir.
