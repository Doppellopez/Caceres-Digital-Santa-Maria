// H4 (prueba): importa la exportacion de Santa Maria en un proyecto vacio y la comprueba.
// Herramienta de editor, sin logica de juego. La lanza herramientas/h4_probar_unity.ps1.
// En la escena de prueba deja la figura de 1,80 m manejable (ControlTeclado.cs).
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public static class PruebaSantaMaria
{
    const string Raiz = "Assets/SantaMaria";

    [Serializable] public class Material_ { public string nombre; public float[] color_lineal; public float rugosidad; public float metalico; public string textura_color; public string textura_normal; public bool sin_repetir; }
    [Serializable] public class Asignacion { public string objeto; public string[] materiales; }
    [Serializable] public class Control { public string objeto; public float[] min; public float[] max; }
    [Serializable] public class Punto { public float[] p; }
    [Serializable] public class Recorrido { public string nombre; public float meta_cota; public Punto[] puntos; }
    [Serializable] public class Camara { public string nombre; public float[] posicion; public float[] frente; public float[] arriba; public float focal_mm; public float sensor_horizontal_mm; public int ancho; public int alto; }
    [Serializable] public class Manifiesto { public string version; public int mallas; public int triangulos; public Material_[] materiales; public Asignacion[] material_por_objeto; public Control[] controles; public Recorrido[] recorridos; public Camara[] camaras; public float[] sol_direccion; }

    static readonly StringBuilder informe = new StringBuilder();
    static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

    static void Anota(string clave, string valor) { informe.AppendLine(clave + " | " + valor); }
    static string F(float v) { return v.ToString("0.###", Inv); }
    static string F(Vector3 v) { return "(" + F(v.x) + ", " + F(v.y) + ", " + F(v.z) + ")"; }

    // Prefab con materiales y colisiones, y paquete para importarlo en otro proyecto.
    static void Empaquetar(Manifiesto man, GameObject modelo)
    {
        string prefab = Raiz + "/SantaMaria.prefab";
        PrefabUtility.SaveAsPrefabAssetAndConnect(modelo, prefab, InteractionMode.AutomatedAction);
        AssetDatabase.SaveAssets();
        var rutas = new List<string> { prefab, Raiz + "/santa_maria.fbx" };
        foreach (var m in man.materiales)
        {
            rutas.Add(Raiz + "/Materiales/" + m.nombre + ".mat");
            foreach (var t in new[] { m.textura_color, m.textura_normal })
                if (!string.IsNullOrEmpty(t)) rutas.Add(Raiz + "/Texturas/" + t);
        }
        var lista = rutas.Distinct().ToArray();
        var paquete = Environment.GetEnvironmentVariable("SANTAMARIA_PAQUETE");
        AssetDatabase.ExportPackage(lista, paquete, ExportPackageOptions.Default);
        var fuera = AssetDatabase.GetDependencies(prefab, true)
            .Where(r => r.StartsWith("Assets/") && !lista.Contains(r)).ToArray();
        Anota("paquete", lista.Length + " recursos, " + new FileInfo(paquete).Length + " bytes; dependencias fuera del paquete: " +
            (fuera.Length == 0 ? "ninguna" : string.Join(", ", fuera)));
    }

    // Blender (X este, Y norte, Z arriba) -> Unity (X este, Y arriba, Z norte).
    static Vector3 U(float[] b) { return new Vector3(b[0], b[2], b[1]); }

    public static void Ejecutar()
    {
        string salida = Environment.GetEnvironmentVariable("SANTAMARIA_SALIDA");
        int codigo = 0;
        try
        {
            Directory.CreateDirectory(salida);
            var man = JsonUtility.FromJson<Manifiesto>(File.ReadAllText(Raiz + "/manifiesto.json"));
            Anota("unity", Application.unityVersion);
            // Sin esto la primera captura sale con materiales a medio compilar (en blanco).
            ShaderUtil.allowAsyncCompilation = false;
            ConfigurarUrp();
            ConfigurarImportacion(man);
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var modelo = (GameObject)PrefabUtility.InstantiatePrefab(
                AssetDatabase.LoadAssetAtPath<GameObject>(Raiz + "/santa_maria.fbx"));
            var renders = modelo.GetComponentsInChildren<MeshRenderer>();
            Anota("raiz_modelo", "posicion " + F(modelo.transform.position) + " giro " + F(modelo.transform.eulerAngles) + " escala " + F(modelo.transform.localScale));
            Anota("mallas", renders.Length + " de " + man.mallas);
            Anota("triangulos", renders.Sum(r => r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3) + " de " + man.triangulos);
            MaterialesAutomaticos(renders);
            AsignarMateriales(man, renders);
            Ejes(man, renders);
            foreach (var r in renders)
                r.gameObject.AddComponent<MeshCollider>().sharedMesh = r.GetComponent<MeshFilter>().sharedMesh;
            Physics.SyncTransforms();
            Empaquetar(man, modelo);
            Iluminar(man);
            var camara = new GameObject("CamaraPrueba").AddComponent<Camera>();
            CarasInvisibles(man, camara);
            Suelo();
            Recorridos(man);
            var control = Persona(man, camara);
            Capturar(camara, man.camaras[0], salida);   // pasada de calentamiento, se sobrescribe
            foreach (var c in man.camaras) Capturar(camara, c, salida);
            CapturarPersona(camara, man, salida);
            ProbarControl(man, control, camara);
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene(), Raiz + "/Prueba.unity");
            AssetDatabase.SaveAssets();
            Anota("fin", "correcto");
        }
        catch (Exception e) { Anota("ERROR", e.ToString()); Debug.LogException(e); codigo = 1; }
        File.WriteAllText(Path.Combine(salida, "informe_unity.txt"), informe.ToString());
        EditorApplication.Exit(codigo);
    }

    static void ConfigurarUrp()
    {
        Directory.CreateDirectory(Raiz + "/Ajustes");
        AssetDatabase.Refresh();
        var datos = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(Raiz + "/Ajustes/Renderer.asset");
        var urp = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(Raiz + "/Ajustes/URP.asset");
        if (urp == null)
        {
            datos = ScriptableObject.CreateInstance<UniversalRendererData>();
            AssetDatabase.CreateAsset(datos, Raiz + "/Ajustes/Renderer.asset");
            urp = UniversalRenderPipelineAsset.Create(datos);
            AssetDatabase.CreateAsset(urp, Raiz + "/Ajustes/URP.asset");
        }
        urp.shadowDistance = 220f;
        urp.shadowCascadeCount = 4;
        urp.msaaSampleCount = 4;
        urp.mainLightShadowmapResolution = 4096;
        PlayerSettings.colorSpace = ColorSpace.Linear;
        GraphicsSettings.defaultRenderPipeline = urp;
        QualitySettings.renderPipeline = urp;
        EditorUtility.SetDirty(urp);
        AssetDatabase.SaveAssets();
        Anota("pipeline", "URP, espacio de color lineal");
    }

    static void ConfigurarImportacion(Manifiesto man)
    {
        var m = (ModelImporter)AssetImporter.GetAtPath(Raiz + "/santa_maria.fbx");
        m.globalScale = 1f;
        m.useFileScale = true;
        m.importCameras = false;
        m.importLights = false;
        m.importAnimation = false;
        m.animationType = ModelImporterAnimationType.None;
        m.importNormals = ModelImporterNormals.Import;
        m.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
        m.isReadable = true;
        m.SaveAndReimport();
        Anota("importacion", "escala de archivo " + m.fileScale.ToString("0.####", Inv) + ", globalScale 1, normales importadas");
        foreach (var mat in man.materiales)
        {
            foreach (var par in new[] { (mat.textura_color, false), (mat.textura_normal, true) })
            {
                if (string.IsNullOrEmpty(par.Item1)) continue;
                var t = (TextureImporter)AssetImporter.GetAtPath(Raiz + "/Texturas/" + par.Item1);
                t.textureType = par.Item2 ? TextureImporterType.NormalMap : TextureImporterType.Default;
                t.sRGBTexture = !par.Item2;
                t.wrapMode = mat.sin_repetir ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
                t.maxTextureSize = 2048;
                t.anisoLevel = 8;
                t.SaveAndReimport();
            }
        }
    }

    static void MaterialesAutomaticos(MeshRenderer[] renders)
    {
        foreach (var m in renders.SelectMany(r => r.sharedMaterials).Where(x => x != null).Distinct().OrderBy(x => x.name))
        {
            var textura = m.HasProperty("_BaseMap") ? m.GetTexture("_BaseMap") : null;
            Anota("material_automatico", m.name + ": " + m.shader.name + ", color " +
                (m.HasProperty("_BaseColor") ? m.GetColor("_BaseColor").ToString() : "-") +
                ", textura " + (textura ? textura.name : "ninguna"));
        }
    }

    static void AsignarMateriales(Manifiesto man, MeshRenderer[] renders)
    {
        Directory.CreateDirectory(Raiz + "/Materiales");
        AssetDatabase.Refresh();
        var shader = Shader.Find("Universal Render Pipeline/Lit");
        var creados = new Dictionary<string, Material>();
        foreach (var d in man.materiales)
        {
            var ruta = Raiz + "/Materiales/" + d.nombre + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(ruta);
            if (m == null) { m = new Material(shader); AssetDatabase.CreateAsset(m, ruta); }
            var color = new Color(d.color_lineal[0], d.color_lineal[1], d.color_lineal[2]).gamma;
            if (!string.IsNullOrEmpty(d.textura_color))
            {
                m.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Raiz + "/Texturas/" + d.textura_color));
                color = Color.white;
            }
            if (!string.IsNullOrEmpty(d.textura_normal))
            {
                m.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(Raiz + "/Texturas/" + d.textura_normal));
                m.EnableKeyword("_NORMALMAP");
            }
            m.SetColor("_BaseColor", color);
            m.SetFloat("_Smoothness", Mathf.Clamp01(1f - d.rugosidad) * 0.6f);
            m.SetFloat("_Metallic", d.metalico);
            EditorUtility.SetDirty(m);
            creados[d.nombre] = m;
        }
        var porObjeto = man.material_por_objeto.ToDictionary(a => a.objeto, a => a.materiales);
        var sinNombre = new List<string>();
        foreach (var r in renders)
        {
            string[] nombres;
            if (!porObjeto.TryGetValue(r.gameObject.name, out nombres)) { sinNombre.Add(r.gameObject.name); continue; }
            // Se empareja por nombre: el orden de las submallas no tiene por que ser el de Blender.
            var importados = r.sharedMaterials.Select(m => m ? m.name : "").ToArray();
            if (importados.Length != nombres.Length || importados.Any(n => !nombres.Contains(n)))
                throw new Exception(r.gameObject.name + ": materiales importados " + string.Join(", ", importados) +
                    "; esperados " + string.Join(", ", nombres));
            r.sharedMaterials = importados.Select(n => creados[n]).ToArray();
        }
        Anota("materiales_asignados", (renders.Length - sinNombre.Count) + " objetos; sin correspondencia de nombre: " +
            (sinNombre.Count == 0 ? "ninguno" : string.Join(", ", sinNombre)));
    }

    static void Ejes(Manifiesto man, MeshRenderer[] renders)
    {
        float peor = 0f;
        foreach (var c in man.controles)
        {
            var r = renders.First(x => x.gameObject.name == c.objeto);
            var vs = r.GetComponent<MeshFilter>().sharedMesh.vertices.Select(v => r.transform.TransformPoint(v)).ToArray();
            var min = vs.Aggregate(Vector3.Min);
            var max = vs.Aggregate(Vector3.Max);
            var emin = U(c.min); var emax = U(c.max);
            float error = Enumerable.Range(0, 3).Max(i => Mathf.Max(Mathf.Abs(min[i] - emin[i]), Mathf.Abs(max[i] - emax[i])));
            peor = Mathf.Max(peor, error);
            Anota("control", c.objeto + ": Unity " + F(min) + " a " + F(max) + "; esperado " + F(emin) + " a " + F(emax) + "; error " + F(error) + " m");
        }
        Anota("ejes_escala_error_max_m", F(peor));
    }

    static void Iluminar(Manifiesto man)
    {
        var sol = new GameObject("Sol").AddComponent<Light>();
        sol.type = LightType.Directional;
        sol.transform.rotation = Quaternion.LookRotation(U(man.sol_direccion));
        sol.color = new Color(1f, 0.97f, 0.92f);
        sol.intensity = 0.95f;
        sol.shadows = LightShadows.Soft;
        RenderSettings.ambientMode = AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.50f, 0.58f, 0.70f);
        RenderSettings.ambientEquatorColor = new Color(0.40f, 0.40f, 0.40f);
        RenderSettings.ambientGroundColor = new Color(0.26f, 0.24f, 0.21f);
    }

    static void Orientar(Camera cam, Camara c)
    {
        cam.transform.position = U(c.posicion);
        cam.transform.rotation = Quaternion.LookRotation(U(c.frente), U(c.arriba));
        float h = 2f * Mathf.Atan(c.sensor_horizontal_mm / (2f * c.focal_mm));
        cam.aspect = (float)c.ancho / c.alto;
        cam.fieldOfView = 2f * Mathf.Atan(Mathf.Tan(h / 2f) / cam.aspect) * Mathf.Rad2Deg;
        cam.nearClipPlane = 0.1f;
        cam.farClipPlane = 1000f;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.55f, 0.62f, 0.70f);
    }

    // Que parte de lo que mira cada camara es una cara vista por detras (Unity no la dibuja).
    static void CarasInvisibles(Manifiesto man, Camera cam)
    {
        Physics.queriesHitBackfaces = true;
        var mallas = new Dictionary<Mesh, (Vector3[], int[])>();
        var total = new Dictionary<string, int>();
        foreach (var c in man.camaras)
        {
            Orientar(cam, c);
            int golpes = 0, deEspaldas = 0, alCielo = 0, concatedral = 0;
            for (int ix = 0; ix < 240; ix++)
                for (int iy = 0; iy < 150; iy++)
                {
                    var rayo = cam.ViewportPointToRay(new Vector3((ix + 0.5f) / 240f, (iy + 0.5f) / 150f, 0f));
                    var origen = rayo.origin; bool primero = true, esDorso = false; string nombre = null; bool delante = false;
                    for (int salto = 0; salto < 12; salto++)
                    {
                        RaycastHit h;
                        if (!Physics.Raycast(origen, rayo.direction, out h, 600f)) break;
                        var malla = ((MeshCollider)h.collider).sharedMesh;
                        (Vector3[], int[]) d;
                        if (!mallas.TryGetValue(malla, out d)) mallas[malla] = d = (malla.vertices, malla.triangles);
                        var t = h.collider.transform;
                        var a = t.TransformPoint(d.Item1[d.Item2[h.triangleIndex * 3]]);
                        var b = t.TransformPoint(d.Item1[d.Item2[h.triangleIndex * 3 + 1]]);
                        var e = t.TransformPoint(d.Item1[d.Item2[h.triangleIndex * 3 + 2]]);
                        bool dorso = Vector3.Dot(Vector3.Cross(b - a, e - a), rayo.direction) > 0f;
                        if (primero) { golpes++; primero = false; esDorso = dorso; nombre = h.collider.name; }
                        if (!dorso) { delante = true; break; }
                        origen = h.point + rayo.direction * 0.002f;
                    }
                    if (!esDorso) continue;
                    deEspaldas++;
                    if (!delante) alCielo++;
                    if (nombre.StartsWith("Concatedral")) concatedral++;
                    total[nombre] = total.TryGetValue(nombre, out var n) ? n + 1 : 1;
                }
            Anota("caras_invisibles", c.nombre + ": " + deEspaldas + " de " + golpes + " rayos (" + F(100f * deEspaldas / Mathf.Max(golpes, 1)) +
                " %), de ellos " + alCielo + " dejan ver el cielo y " + concatedral + " son de la concatedral");
        }
        foreach (var p in total.OrderByDescending(p => p.Value).Take(25))
            Anota("caras_invisibles_objeto", p.Key + ": " + p.Value);
        Physics.queriesHitBackfaces = false;
    }

    static void Suelo()
    {
        // Solo cuenta el terreno: se mira desde arriba en la plaza.
        var terreno = GameObject.Find("Terreno_interpolado").GetComponent<MeshCollider>();
        int total = 0, sin = 0;
        Physics.queriesHitBackfaces = false;
        for (float x = -10f; x <= 20f; x += 0.5f)
            for (float z = -5f; z <= 25f; z += 0.5f)
            {
                total++;
                RaycastHit h;
                if (!terreno.Raycast(new Ray(new Vector3(x, 100f, z), Vector3.down), out h, 200f)) sin++;
            }
        Anota("terreno_plaza", sin + " de " + total + " puntos sin suelo pisable desde arriba");
    }

    static void Recorridos(Manifiesto man)
    {
        foreach (var rec in man.recorridos)
        {
            var objeto = new GameObject("Caminante");
            var inicio = U(rec.puntos[0].p);
            var cc = objeto.AddComponent<CharacterController>();
            cc.height = 1.8f; cc.radius = 0.3f; cc.center = new Vector3(0f, 0.9f, 0f);
            cc.stepOffset = 0.3f; cc.slopeLimit = 45f; cc.skinWidth = 0.03f; cc.minMoveDistance = 0f;
            objeto.transform.position = inicio + Vector3.up * 0.3f;
            Physics.SyncTransforms();
            float caida = 0f, minimo = float.MaxValue; bool completo = true;
            for (int i = 1; i < rec.puntos.Length && completo; i++)
            {
                var meta = U(rec.puntos[i].p);
                int pasos = 0;
                while (true)
                {
                    var resto = meta - objeto.transform.position; resto.y = 0f;
                    if (resto.magnitude < 0.12f) break;
                    if (++pasos > 2500) { completo = false; break; }
                    caida = cc.isGrounded ? -2f : caida - 9.81f * 0.02f;
                    var avance = resto.normalized * Mathf.Min(1.4f * 0.02f, resto.magnitude);
                    cc.Move(avance + Vector3.up * caida * 0.02f);
                    minimo = Mathf.Min(minimo, objeto.transform.position.y);
                }
                Anota("recorrido_tramo", rec.nombre + " tramo " + i + ": " + (completo ? "llega" : "se queda") + " en " + F(objeto.transform.position) + ", meta " + F(meta));
            }
            for (int i = 0; i < 60; i++) cc.Move(Vector3.down * 0.05f);
            Anota("recorrido", rec.nombre + ": " + (completo ? "completado" : "NO completado") + ", cota final " + F(objeto.transform.position.y) +
                (rec.meta_cota > -900f ? " (umbral " + F(rec.meta_cota) + ")" : "") + ", cota minima " + F(minimo));
            UnityEngine.Object.DestroyImmediate(objeto);
        }
    }

    // Figura de 1,80 m ante la portada: referencia de escala y personaje de recorrido.
    static ControlTeclado Persona(Manifiesto man, Camera camara)
    {
        var rec = man.recorridos[0];
        var figura = new GameObject("Referencia_180cm");   // origen en los pies
        figura.transform.position = U(rec.puntos[1].p) + Vector3.up * 0.05f;
        var haciaPuerta = U(rec.puntos[2].p) - U(rec.puntos[1].p);
        haciaPuerta.y = 0f;
        figura.transform.rotation = Quaternion.LookRotation(haciaPuerta.normalized);
        var m = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        m.SetColor("_BaseColor", new Color(0.75f, 0.12f, 0.08f));
        AssetDatabase.CreateAsset(m, Raiz + "/Materiales/Referencia.mat");
        Pieza(figura, PrimitiveType.Capsule, "Cuerpo", new Vector3(0f, 0.9f, 0f), new Vector3(0.55f, 0.9f, 0.55f), m);
        Pieza(figura, PrimitiveType.Cube, "Frente", new Vector3(0f, 1.55f, 0.26f), new Vector3(0.3f, 0.09f, 0.08f), m);
        var cc = figura.AddComponent<CharacterController>();
        cc.height = 1.8f; cc.radius = 0.3f; cc.center = new Vector3(0f, 0.9f, 0f);
        cc.stepOffset = 0.3f; cc.slopeLimit = 45f; cc.skinWidth = 0.03f; cc.minMoveDistance = 0f;
        var control = figura.AddComponent<ControlTeclado>();
        camara.tag = "MainCamera";
        control.camara = camara.transform;
        return control;
    }

    static void Pieza(GameObject padre, PrimitiveType tipo, string nombre, Vector3 posicion, Vector3 escala, Material m)
    {
        var p = GameObject.CreatePrimitive(tipo);
        p.name = nombre;
        UnityEngine.Object.DestroyImmediate(p.GetComponent<Collider>());
        p.transform.SetParent(padre.transform, false);
        p.transform.localPosition = posicion;
        p.transform.localScale = escala;
        p.GetComponent<MeshRenderer>().sharedMaterial = m;
    }

    // Mueve la figura como lo harian las teclas y el raton (sin modo Play) y la deja en el inicio.
    static void ProbarControl(Manifiesto man, ControlTeclado control, Camera camara)
    {
        var t = control.transform;
        Physics.SyncTransforms();
        control.Preparar();
        var p0 = t.position; var frente = t.forward;
        System.Action<float, float, float, float> pasos = (avance, lateral, vuelta, segundos) =>
        { for (int i = 0; i < Mathf.RoundToInt(segundos / 0.02f); i++) control.Paso(avance, lateral, vuelta, 0f, false, 0.02f); };
        pasos(0f, 0f, 0f, 0.5f);
        pasos(1f, 0f, 0f, 1f);
        Anota("control_avanzar", "1 s adelante: " + F(Vector3.Dot(t.position - p0, frente)) + " m");
        pasos(1f, 0f, 0f, 8f);
        var puerta = U(man.recorridos[0].puntos[2].p);
        Anota("control_choque", "9 s contra la portada: queda en " + F(t.position) + ", a " + F(Vector3.Dot(t.position - puerta, frente)) +
            " m del punto ante la puerta (negativo = no lo ha rebasado), cota " + F(t.position.y));
        var antes = t.position; pasos(-1f, 0f, 0f, 1f);
        Anota("control_retroceder", "1 s atras: " + F(Vector3.Dot(t.position - antes, frente)) + " m");
        antes = t.position; pasos(0f, 1f, 0f, 1f);
        Anota("control_lateral", "1 s a la derecha: " + F(Vector3.Dot(t.position - antes, t.right)) + " m");
        float rumbo = t.eulerAngles.y; pasos(0f, 0f, 1f, 0.9f);
        Anota("control_giro", "0,9 s girando: " + F(Mathf.DeltaAngle(rumbo, t.eulerAngles.y)) + " grados");
        control.Volver();
        rumbo = t.eulerAngles.y;
        control.Mirar(10f, 8f); control.ColocarCamara();
        Anota("control_raton", "raton (10, 8): camara gira " + F(Mathf.DeltaAngle(rumbo, camara.transform.eulerAngles.y)) +
            " grados y se inclina " + F(-Mathf.DeltaAngle(0f, camara.transform.eulerAngles.x)) + " grados hacia arriba");
        control.Volver();
        camara.ResetAspect();
        camara.fieldOfView = 60f;
        control.ColocarCamara();
        var foto = control.HacerFoto(Path.Combine(Path.GetTempPath(), "santamaria_foto_prueba"));
        Anota("control_foto", Path.GetFileName(foto) + ", " + new FileInfo(foto).Length + " bytes");
        File.Copy(foto, Path.Combine(Environment.GetEnvironmentVariable("SANTAMARIA_SALIDA"), "unity_foto_control.png"), true);
        File.Delete(foto);
        Anota("control_volver", "a " + F(Vector3.Distance(t.position, p0)) + " m del inicio");
        camara.ResetAspect();
        camara.fieldOfView = 60f;
        control.ColocarCamara();
        // En la vista Scene la figura se sigue viendo; en modo Play la camara va en sus ojos y la oculta.
        foreach (var r in control.GetComponentsInChildren<Renderer>()) r.enabled = true;
    }

    static void Capturar(Camera cam, Camara c, string salida)
    {
        Orientar(cam, c);
        var rt = new RenderTexture(c.ancho, c.alto, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
        var peticion = new UniversalRenderPipeline.SingleCameraRequest { destination = rt };
        if (RenderPipeline.SupportsRenderRequest(cam, peticion)) RenderPipeline.SubmitRenderRequest(cam, peticion);
        else { cam.targetTexture = rt; cam.Render(); cam.targetTexture = null; Anota("aviso", "render sin SubmitRenderRequest"); }
        RenderTexture.active = rt;
        var img = new Texture2D(c.ancho, c.alto, TextureFormat.RGB24, false);
        img.ReadPixels(new Rect(0, 0, c.ancho, c.alto), 0, 0);
        img.Apply();
        RenderTexture.active = null;
        File.WriteAllBytes(Path.Combine(salida, "unity_" + c.nombre + ".png"), img.EncodeToPNG());
        rt.Release();
        Anota("captura", c.nombre);
    }

    static void CapturarPersona(Camera cam, Manifiesto man, string salida)
    {
        var a = U(man.recorridos[0].puntos[0].p);
        var b = U(man.recorridos[0].puntos[2].p);
        var lejos = a + (a - b).normalized * 3f + Vector3.up * 1.65f;
        var mira = b + Vector3.up * 2.2f;
        var frente = (mira - lejos).normalized;
        var c = new Camara
        {
            nombre = "persona_portada", ancho = 1600, alto = 1000, focal_mm = 28f, sensor_horizontal_mm = 36f,
            posicion = new[] { lejos.x, lejos.z, lejos.y }, frente = new[] { frente.x, frente.z, frente.y }, arriba = new[] { 0f, 0f, 1f }
        };
        Capturar(cam, c, salida);
    }
}
