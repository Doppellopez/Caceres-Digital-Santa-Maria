// Control por teclado y raton de la figura de 1,80 m, para recorrer la maqueta en modo Play.
// Herramienta de prueba del proyecto vacio: no forma parte del paquete ni de Qazrix.
// Usa el gestor de entrada clasico (Input Manager), que es el activo en ese proyecto.
using System;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

[RequireComponent(typeof(CharacterController))]
public class ControlTeclado : MonoBehaviour
{
    public Transform camara;
    public float velocidad = 1.6f;        // m/s andando
    public float carrera = 4.5f;          // m/s con Mayusculas
    public float giro = 100f;             // grados/s
    public float inclinacion = 60f;       // grados/s al mirar arriba o abajo
    public float sensibilidadRaton = 2.5f; // grados por unidad de los ejes "Mouse X" y "Mouse Y"
    public bool terceraPersona = false;   // por defecto la camara va en los ojos de la figura

    CharacterController cc;
    Vector3 inicio;
    Quaternion giroInicio;
    float mirada;                         // grados, positivo hacia arriba
    float caida;
    bool fotoPendiente;
    string aviso = "";
    float avisoHasta;

    public void Preparar()
    {
        cc = GetComponent<CharacterController>();
        inicio = transform.position;
        giroInicio = transform.rotation;
        mirada = 0f;
        caida = 0f;
    }

    void Awake() { Preparar(); }

    void Start()
    {
        var c = camara ? camara.GetComponent<Camera>() : null;
        if (c) { c.ResetAspect(); c.fieldOfView = 60f; c.nearClipPlane = 0.1f; }
        Atrapar(true);
    }

    static float Eje(bool positivo, bool negativo) { return (positivo ? 1f : 0f) - (negativo ? 1f : 0f); }
    static bool Pulsada(KeyCode a, KeyCode b) { return Input.GetKey(a) || Input.GetKey(b); }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.V)) terceraPersona = !terceraPersona;
        if (Input.GetKeyDown(KeyCode.R)) Volver();
        // El boton izquierdo hace una foto y, si el raton estaba suelto, vuelve a atraparlo.
        // Esc lo suelta: suelto no gira la camara, para poder usar el editor.
        if (Input.GetMouseButtonDown(0)) { Atrapar(true); fotoPendiente = true; }
        if (Input.GetKeyDown(KeyCode.Escape)) Atrapar(false);
        else if (Cursor.lockState == CursorLockMode.Locked)
            Mirar(Input.GetAxisRaw("Mouse X"), Input.GetAxisRaw("Mouse Y"));
        Paso(Eje(Pulsada(KeyCode.W, KeyCode.UpArrow), Pulsada(KeyCode.S, KeyCode.DownArrow)),
             Eje(Input.GetKey(KeyCode.D), Input.GetKey(KeyCode.A)),
             Eje(Pulsada(KeyCode.E, KeyCode.RightArrow), Pulsada(KeyCode.Q, KeyCode.LeftArrow)),
             Eje(Input.GetKey(KeyCode.PageUp), Input.GetKey(KeyCode.PageDown)),
             Pulsada(KeyCode.LeftShift, KeyCode.RightShift), Time.deltaTime);
    }

    void LateUpdate()
    {
        ColocarCamara();
        if (!fotoPendiente) return;
        fotoPendiente = false;
        try { aviso = "Foto guardada: " + HacerFoto(CarpetaDeFotos()); Debug.Log(aviso); }
        catch (Exception e) { aviso = "No se pudo guardar la foto: " + e.Message; Debug.LogException(e); }
        avisoHasta = Time.unscaledTime + 4f;
    }

    static void Atrapar(bool atrapado)
    {
        Cursor.lockState = atrapado ? CursorLockMode.Locked : CursorLockMode.None;
        Cursor.visible = !atrapado;
    }

    void OnDisable() { Atrapar(false); }

    // En el editor, carpeta "Fotos" junto a Assets (fuera, para que Unity no las importe).
    public static string CarpetaDeFotos()
    {
        var raiz = Application.isEditor ? Path.GetDirectoryName(Application.dataPath) : Application.persistentDataPath;
        return Path.Combine(raiz, "Fotos");
    }

    // Guarda en PNG lo que ve la camara (sin los cuadros de texto) y devuelve la ruta.
    public string HacerFoto(string carpeta, int ancho = 1920)
    {
        var c = camara.GetComponent<Camera>();
        int alto = Mathf.Max(1, Mathf.RoundToInt(ancho / c.aspect));
        var destino = new RenderTexture(ancho, alto, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
        var anterior = RenderTexture.active;
        var imagen = new Texture2D(ancho, alto, TextureFormat.RGB24, false);
        try
        {
            var peticion = new UniversalRenderPipeline.SingleCameraRequest { destination = destino };
            if (!RenderPipeline.SupportsRenderRequest(c, peticion))
                throw new InvalidOperationException("el pipeline no admite la captura");
            RenderPipeline.SubmitRenderRequest(c, peticion);
            RenderTexture.active = destino;
            imagen.ReadPixels(new Rect(0, 0, ancho, alto), 0, 0);
            imagen.Apply();
            Directory.CreateDirectory(carpeta);
            var ruta = Path.Combine(carpeta, "foto_" + DateTime.Now.ToString("yyyyMMdd_HHmmss_fff") + ".png");
            File.WriteAllBytes(ruta, imagen.EncodeToPNG());
            return ruta;
        }
        finally
        {
            RenderTexture.active = anterior;
            destino.Release();
            if (Application.isPlaying) { Destroy(destino); Destroy(imagen); }
            else { DestroyImmediate(destino); DestroyImmediate(imagen); }
        }
    }

    // Giro con el raton: el desplazamiento ya es por fotograma, no se multiplica por el tiempo.
    public void Mirar(float dx, float dy)
    {
        transform.Rotate(0f, dx * sensibilidadRaton, 0f);
        mirada = Mathf.Clamp(mirada + dy * sensibilidadRaton, -60f, 75f);
    }

    // Un paso de movimiento; las entradas van de -1 a 1.
    public void Paso(float avance, float lateral, float vuelta, float mira, bool correr, float dt)
    {
        transform.Rotate(0f, vuelta * giro * dt, 0f);
        mirada = Mathf.Clamp(mirada + mira * inclinacion * dt, -60f, 75f);
        var direccion = Vector3.ClampMagnitude(transform.forward * avance + transform.right * lateral, 1f);
        caida = cc.isGrounded ? -2f : caida - 9.81f * dt;
        cc.Move((direccion * (correr ? carrera : velocidad) + Vector3.up * caida) * dt);
        if (transform.position.y < inicio.y - 30f) Volver();   // se ha salido de la maqueta
    }

    public void Volver()
    {
        cc.enabled = false;
        transform.SetPositionAndRotation(inicio, giroInicio);
        cc.enabled = true;
        mirada = 0f;
        caida = 0f;
    }

    public void ColocarCamara()
    {
        if (!camara) return;
        var ojos = transform.position + Vector3.up * 1.65f;
        var rotacion = Quaternion.Euler(-mirada, transform.eulerAngles.y, 0f);
        var posicion = ojos;
        if (terceraPersona)
        {
            var punto = ojos + Vector3.up * 0.35f;
            var atras = rotacion * Vector3.back;
            float distancia = 4.5f;
            RaycastHit golpe;   // la camara no atraviesa muros
            if (Physics.SphereCast(punto, 0.2f, atras, out golpe, distancia, ~0, QueryTriggerInteraction.Ignore))
                distancia = golpe.distance;
            posicion = punto + atras * distancia;
        }
        camara.SetPositionAndRotation(posicion, rotacion);
        foreach (var r in GetComponentsInChildren<Renderer>()) r.enabled = terceraPersona;
    }

    void OnGUI()
    {
        if (Time.unscaledTime < avisoHasta) GUI.Box(new Rect(8f, Screen.height - 34f, Screen.width - 16f, 26f), aviso);
        GUI.Box(new Rect(8f, 8f, 330f, 144f),
            "Ratón: girar la cámara    Esc: soltarlo\nBotón izquierdo: hacer una foto\n" +
            "W / S o flechas: avanzar y retroceder\nA / D: paso lateral\nQ / E o flechas: girar    Mayús: correr\n" +
            "RePág / AvPág: mirar arriba y abajo\nV: primera o tercera persona\nR: volver al inicio");
    }
}
