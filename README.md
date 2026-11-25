# Cáceres Digital — Santa María

## Briefing para Jorge

Jorge, la idea es separar temporalmente la construcción de Cáceres del desarrollo de Qazrix. No abandonar el juego: darle un escenario que merezca la pena recorrer.

Ya tienes una maqueta tridimensional de unos 150 × 150 metros alrededor de la plaza de Santa María, construida a partir del levantamiento cartográfico municipal de 2012. No son edificios colocados al azar: tenemos plantas, cotas y trazados de cubiertas reales. La concatedral incluye un primer ensayo de refinamiento, todavía aproximado. Ahora viene la parte interesante: transformar esa maqueta en una plaza reconocible, con tu propio criterio y con Claude Code como ayudante.

## Arranca en diez minutos

1. Descomprime el ZIP en una carpeta independiente de Qazrix y ábrela con Claude Code.
2. Abre Blender, elimina el cubo inicial e importa `modelos/v0.3/santa_maria_v0_3.glb` mediante File → Import → glTF 2.0. Guarda como `blender/santa_maria.blend`. Si prefieres trabajar por scripts, pide a Claude que automatice la importación. No hace falta aprender toda la interfaz de Blender.
3. Compara `referencias/concatedral_closeup_v0_3.png` con fotos reales de la concatedral. Es una demostración de edición, no el aspecto que debes copiar.
4. Pega el mensaje de arranque que encontrarás al final de este briefing. Primero comprueba que puedes abrir el modelo y sacar una imagen desde una cámara fija. Después elige tú qué fachada mejorar.

## La primera victoria

Que una fachada de Santa María resulte reconocible en una captura a altura de peatón: piedra, puertas, ventanas y proporciones. Puedes comenzar por la propia concatedral o escoger el Palacio Episcopal si tienes mejores fotos. No intentes terminar toda la iglesia, y mucho menos toda la ciudad, en esa primera sesión.

El modelo de partida es editable por objetos; las cubiertas y fachadas están separadas. No hay texturas fotográficas. Busca imágenes utilizables, o toma tus propias fotos, y decide con Claude cómo proyectarlas sobre la geometría y qué elementos necesitan relieve real. Si algo del modelo base está mal, corrígelo: no tienes que aceptar nuestras aproximaciones.

## Cómo sabrás que funciona

Una foto real y un render desde un punto parecido deberían mostrar el mismo edificio. Comprueba también que no hay agujeros visibles ni elementos flotando. Guarda el antes y el después. Cuando estés contento con una fachada, pasa a la siguiente. No hace falta que el modelo sea perfecto para empezar a disfrutar del resultado.

Más adelante exportaremos una versión a Unity y la recorreremos con el personaje de Qazrix. Mientras tanto, ninguna misión, NPC ni mecánica del juego tiene que entrar en este proyecto.

## Mensaje de arranque para Claude Code

> Lee README.md y CLAUDE.md. Ayúdame a abrir el modelo v0.3 en Blender y guardarlo como un .blend independiente. Comprueba escala y orientación, localiza la concatedral y prepara una cámara a altura de peatón frente a una fachada visible desde la plaza. Saca un render real del modelo y muéstrame qué se ve mal. No modifiques todavía otros edificios ni Qazrix. Cuando tengamos esa primera captura, quiero elegir contigo una fachada y mejorarla usando referencias fotográficas reales, en pasos pequeños y verificables.
