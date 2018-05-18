
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Linq;

public class MainControl : MonoBehaviour
{

    /// VARIVAVEIS

    public Renderer crend;  ///RENDER CHAO
    RoadCreator rC;         ///PROGRAMA CRIAR RUAS

    public GameObject Connector; ///CONNECTOR/ESTACAO
    public TrackShapeHolder tsH;    ///HOLDER DE FORMAS DE TRILHOS


    /// LISTA DE CONNECOES/TRILHOS

    public List<Connections> Mconexoes = new List<Connections>();
    public List<BasicRoad> trilhos = new List<BasicRoad>();

    /// TRACK PUT

    GameObject st, en, track;

    public LayerMask LMask;
    int clickCounter = 0;
    bool tracks = false;
    // bool start = false; p1, , p4
    Vector3 p1, p2, p3, p4;

    /// Track TEMP
    bool ontrilho = false;
    BasicRoad otrilho;
    float ftp;


    public Material materialTracks;

    void Start()
    {
        ///SET FLOOR
        clearFloor();
        rC = GetComponent<RoadCreator>();
    }

    void clearFloor()
    {
        Texture2D tex = crend.material.mainTexture as Texture2D;
        for (int x = 0; x < tex.width; x++)
            for (int y = 0; y < tex.height; y++)
                tex.SetPixel(x, y, Color.grey);

        tex.Apply();
    }



    void Update()
    {

        ShowShader();
        putTrack();


        ///CLEAR;
        if (Input.GetMouseButtonUp(1))
        {

            Destroy(st);

            Clear();
        }

        if (tracks) return;


        ///TRACK PUT START
        if (Input.GetKeyDown(KeyCode.Alpha1))
        {
            Clear();
            ClearNullConnecitons();

            p1 = Vector3.zero;
            p2 = Vector3.zero;
            p3 = Vector3.zero;
            p4 = Vector3.zero;
            tracks = true;
        }


    }

    void Clear()
    {
        clickCounter = 0;
        tracks = false;
        // start = false;
        st = null;
        en = null;
        track = null;
    }





    void putTrack()
    {
        if (!tracks) return;

        ontrilho = false;
        RaycastHit hit;
        Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);

        if (Physics.Raycast(ray, out hit, 10000, LMask))
        {

            //  bool ok = false;
            Vector3 p = GetPoint(hit.point + Vector3.up * 0.114f, 0.2f, 0.6f);
            if (p != hit.point)
            {
                ray = new Ray(p + Vector3.up, 2 * Vector3.down);
                Physics.Raycast(ray, out hit, 1000, LMask);
            }
            // Clear();
            clearFloor();
            ColorConnectors(hit);

            //if(start)
            // {
            switch (clickCounter)
            {
                case 1:
                    track.GetComponent<MeshFilter>().mesh =
                        rC.ExtrudeMesh(tsH.Shapes[0], p1, (p1 + p) / 2, (p1 + p) / 2, p);
                    break;
                case 2:
                    track.GetComponent<MeshFilter>().mesh =
                        rC.ExtrudeMesh(tsH.Shapes[0], p1, p, p, p4);
                    break;

                case 3:
                    track.GetComponent<MeshFilter>().mesh =
                        rC.ExtrudeMesh(tsH.Shapes[0], p1, p2, p, p4);
                    break;



            }
            //}

            if (Input.GetMouseButtonUp(0))// && ok)
            {
                ///COR PARSE
                switch (clickCounter)
                {
                    case 0:
                        p1 = p;
                        st = Instantiate(Connector) as GameObject;
                        if (ontrilho)
                        {
                            otrilho.conections.Add(st.GetComponent<Connections>(), ftp);
                            st.GetComponent<Connections>().trilhos.Add(otrilho);
                        }
                        st.transform.position = p;
                        track = createTrack();
                        break;

                    case 1:

                        en = Instantiate(Connector) as GameObject;
                        if (ontrilho)
                        {
                            otrilho.conections.Add(en.GetComponent<Connections>(), ftp);
                            en.GetComponent<Connections>().trilhos.Add(otrilho);
                        }
                        en.transform.position = p;


                        p4 = p;
                        break;

                    case 2:
                        p2 = p;

                        break;

                    case 3:
                        p3 = p;



                        Mconexoes.Add(st.GetComponent<Connections>());

                        st.name = Mconexoes.Count.ToString();
                        Mconexoes.Add(en.GetComponent<Connections>());

                        en.name = Mconexoes.Count.ToString();




                        track.AddComponent<BasicRoad>();
                        BasicRoad bR = track.GetComponent<BasicRoad>();
                        bR.set(p1, p2, p3, p4, rC.getDist());
                        bR.conections.Add(st.GetComponent<Connections>(), 0);
                        bR.conections.Add(en.GetComponent<Connections>(), 1);

                        trilhos.Add(bR);

                        en.GetComponent<Connections>().trilhos.Add(bR);
                        st.GetComponent<Connections>().trilhos.Add(bR);

                        clearTwoConnections(en.GetComponent<Connections>(), st.GetComponent<Connections>());
                        ClearNullConnecitons();
                        Clear();


                        break;
                }
                clickCounter++;





            }
        }


    }

    GameObject createTrack()
    {
        GameObject tg = new GameObject();
        tg.AddComponent<MeshFilter>();
        tg.AddComponent<MeshRenderer>();
        tg.GetComponent<MeshRenderer>().material = materialTracks;

        return tg;
        ///ASSIGN TO BASICROAD

    }


    void ColorConnectors(RaycastHit hit)
    //,Vector3 p)
    {
        if (crend == null || crend.sharedMaterial == null || crend.sharedMaterial.mainTexture == null)// || meshCollider == null)
            return;

        Texture2D tex = crend.material.mainTexture as Texture2D;

        Vector2 pixelUV = hit.textureCoord;
        pixelUV.x *= tex.width;
        pixelUV.y *= tex.height;


        for (int i = -5; i < 5; i++)
            for (int j = -5; j < 5; j++)
                if (Mathf.Sqrt(Mathf.Pow(i, 2) + Mathf.Pow(j, 2)) < 5)
                    tex.SetPixel((int)pixelUV.x + i, (int)pixelUV.y + j, Color.yellow);
        tex.Apply();

    }

    void ClearNullConnecitons()
    {
        ///REMOVE NULLS
        Mconexoes = Mconexoes.Distinct().ToList();
        Mconexoes.RemoveAll(item => item == null);

        trilhos = trilhos.Distinct().ToList();
        trilhos.RemoveAll(item => item == null);

        foreach (Connections c in Mconexoes)
        {
            ///REMOVE NULLS
            c.trilhos = c.trilhos.Distinct().ToList();
            c.trilhos.RemoveAll(item => item == null);

        }

    }

    void clearOneConnection(Connections c1, out Connections c2)
    {

        c2 = c1;

        ///CONECTORES MUITO PROXIMOS
        foreach (Connections c in Mconexoes)
        {
            if (c != c1)
                if (Vector3.Distance(c.transform.position, c1.transform.position) < 0.2f)
                {
                    c.trilhos.AddRange(c1.trilhos);
                    Mconexoes.Remove(c1);
                    print(c.name);
                    ///pra cada trilho, troca c1 por c
                    foreach (BasicRoad d in c1.trilhos)
                    {
                        if (!d.conections.ContainsKey(c)) { print(d.name + " " + c.name); d.conections.Add(c, d.conections[c1]); }
                    }
                    Destroy(c1.gameObject);
                    c2 = c;
                    return;
                }

        }


    }



    void clearTwoConnections(Connections stc, Connections enc)
    {

        ClearNullConnecitons();

        clearOneConnection(enc, out enc);
        ClearNullConnecitons();
        clearOneConnection(stc, out stc);

        Clear1:
        ClearNullConnecitons();

        ///trilho EM trilho
        float distance = 0.2f, f1 = 0, f2 = 0;
        Vector3 p = Vector3.zero;
        foreach (BasicRoad b1 in trilhos)
        {
            foreach (BasicRoad b2 in trilhos)
                if (b2 != b1 && !b1.conections.Keys.Any(c => b2.conections.Keys.Contains(c)))
                {

                    for (int i = 0; i < rC.quantidades; i++)
                        for (int j = 0; j < rC.quantidades; j++)
                        {
                            Vector3 p1 = rC.getPoint2((float)i / (float)rC.quantidades, b1.p1, b1.p2, b1.p3, b1.p4),
                                p2 = rC.getPoint2((float)j / (float)rC.quantidades, b2.p1, b2.p2, b2.p3, b2.p4);
                            if (Vector3.Distance(p1, p2) < distance)
                            {
                                f1 = (float)i / (float)rC.quantidades;
                                f2 = (float)j / (float)rC.quantidades;
                                distance = Vector3.Distance(p1, p2);
                                p = p1;
                            }

                        }
                    if (distance < 0.2f) { insert(p, b1, f1, b2, f2); goto Clear1; }
                }

        }

    }

    void insert(Vector3 p, BasicRoad t1, float f1, BasicRoad t2, float f2)
    {
        GameObject tt = Instantiate(Connector) as GameObject;
        tt.transform.position = p;
        tt.GetComponent<Connections>().trilhos.Add(t1);
        tt.GetComponent<Connections>().trilhos.Add(t2);
        t1.conections.Add(tt.GetComponent<Connections>(), f1);
        t2.conections.Add(tt.GetComponent<Connections>(), f2);
        Mconexoes.Add(tt.GetComponent<Connections>());
    }



    bool checkPoint(float x1, float x2, float xm)
    {
        if (x1 < x2)
        {
            if (xm > x1 && xm < x2) return true;
            else return false;
        }
        else
        {
            if (xm > x2 && xm < x1) return true;
            else return false;
        }
    }




    Vector3 GetPoint(Vector3 p, float d, float d2)
    {
        float d1 = d2;
        Vector3 final = p;
        ///CLOSEST CONNECTION
        foreach (Connections g in Mconexoes)
        {
            if (Vector3.Distance(g.transform.position, p) < d2)
            {

                //   print(g.name);
                d2 = Vector3.Distance(g.transform.position, p);
                final = g.transform.position;

            }
        }
        if (d2 != d1) return final;
        d1 = d;
        ///PROCURA UM PONTO EM TODAS AS RUAS QUE ESTEJA
        //bool get = false;

        foreach (BasicRoad br in trilhos)
        {

            for (int i = 0; i < rC.quantidades; i++)
            {
                ///pega cada ponto e ve a proximidade, pega a menor das menores que d e retorna como ponto
                Vector3 tp = rC.getPoint2((float)i / (float)rC.quantidades, br.p1, br.p2, br.p3, br.p4);

                if (Vector3.Distance(tp, p) < d)
                {
                    final = tp;
                    d = Vector3.Distance(tp, p);
                    ontrilho = true;
                    otrilho = br;
                    ftp = (float)i / (float)rC.quantidades;
                }

            }


        }


        return final;

    }
    void ShowShader()
    {

    }


}
