
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Linq;

public class MainControl : MonoBehaviour
{

    // Use this for initialization
    void Start()
    {
        ///SET FLOOR
        clearFloor();
    }
    public Renderer crend;
    void clearFloor()
    {
        Texture2D tex = crend.material.mainTexture as Texture2D;
        for (int x = 0; x < tex.width; x++)
            for (int y = 0; y < tex.height; y++)
                tex.SetPixel(x, y, Color.grey);

        tex.Apply();
        print("aaaaa");
    }
    public GameObject BasicRoad, Block;

    bool showGrid = false;
    public float GridSize, SquareSize;
    // Update is called once per frame
    void Update()
    {
        // print(Mconexoes.Count);
        PutStreet();
        ShowShader();
        //   PutIntersection();
        //  print(connections.Count);
        // print(street + " " + intersection);
        ///CLEAR;
        if (Input.GetMouseButtonUp(1))
        {
            Destroy(ToPlace);
            Destroy(st);

            Clear();
        }

        if (street) return;// || intersection) 


        ///PUT STREETS
        if (Input.GetKeyDown(KeyCode.Alpha2) && !street)
        {
            ClearNullConnecitons();

            ToPlace = Instantiate(BasicRoad) as GameObject;
            //street = true;
            street = true;
            //Ctemp = new List<Connections>();
        }


    }

    void Clear()
    {
        street = false;
        start = false;
        ToPlace = null;
        st = null;
    }

    GameObject ToPlace, st, en;
    public LayerMask LMask;

    bool street = false;
    bool start = false, finish = false;
    Vector3 origin = Vector3.zero, end = Vector3.zero;


    public List<Connections> Mconexoes = new List<Connections>();
    //  List<Connections> Ctemp = new List<Connections>();

    void PutStreet()
    {
        //   print(street);
        if (!street) return;

        RaycastHit hit;
        Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);

        if (Physics.Raycast(ray, out hit, 10000, LMask))
        {

            //  bool ok = false;
            Vector3 p = GetPoint(hit.point + Vector3.up * 0.114f, 0.2f, 0.6f);

            ColorConnectors(hit);


            //     print(ok);
            if (!start) ToPlace.transform.position = p;
            else
            {
                ToPlace.transform.position = (origin + p) / 2;
                ToPlace.transform.localScale = new Vector3(2 * Vector3.Distance(p, origin) * 0.05f, 1, 0.01f);
                ToPlace.transform.rotation = Quaternion.Euler(0, Vector3.SignedAngle(Vector3.right, p - origin, Vector3.up), 0);
            }
            if (Input.GetMouseButtonUp(0))// && ok)
            {
                ///COR PARSE


                if (!start)
                {
                    origin = p;

                    st = Instantiate(Block) as GameObject;
                    st.name = Mconexoes.Count.ToString();
                    st.transform.position = p;
                    //Ctemp.Add(st.GetComponent<Connections>());

                    start = true;
                }
                else
                {
                    Mconexoes.Add(st.GetComponent<Connections>());

                    en = Instantiate(Block) as GameObject;
                    en.name = Mconexoes.Count.ToString();
                    en.transform.position = p;
                    Mconexoes.Add(en.GetComponent<Connections>());


                    en.GetComponent<Connections>().Conexoes.Add(st.GetComponent<Connections>());
                    st.GetComponent<Connections>().Conexoes.Add(en.GetComponent<Connections>());
                    end = p;
                    clearTwoConnections(en.GetComponent<Connections>(), st.GetComponent<Connections>());
                    //while (!)
                    //{
                    //    print("ciclo");
                    //}

                    Clear();
                    ClearColisao();

                }




            }
        }

    }


    void ColorConnectors(RaycastHit hit)
    {
        Renderer rend = hit.transform.GetComponent<Renderer>();
        MeshCollider meshCollider = hit.collider as MeshCollider;

        if (rend == null || rend.sharedMaterial == null || rend.sharedMaterial.mainTexture == null || meshCollider == null)
            return;

        Texture2D tex = rend.material.mainTexture as Texture2D;
        Vector2 pixelUV = hit.textureCoord;
        pixelUV.x *= tex.width;
        pixelUV.y *= tex.height;


        tex.SetPixel((int)pixelUV.x, (int)pixelUV.y, Color.yellow);
        tex.Apply();
 
    }

    void ClearNullConnecitons()
    {
        ///REMOVE NULLS
        Mconexoes = Mconexoes.Distinct().ToList();
        Mconexoes.RemoveAll(item => item == null);
        foreach (Connections c in Mconexoes)
        {

            ///REMOVE NULLS
            c.Conexoes.RemoveAll(item => item == null);
            c.Conexoes = c.Conexoes.Distinct().ToList();

            // print(c.name + " " + c.transform.position + " " + c.Conexoes.Count);
            ///
            foreach (Connections d in c.Conexoes)
            {
                if (!d.Conexoes.Contains(c)) { print(d.name + " " + c.name); d.Conexoes.Add(c); }
            }

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
                    c.Conexoes.AddRange(c1.Conexoes);
                    Mconexoes.Remove(c1);
                    print(c.name);
                    foreach (Connections d in c1.Conexoes)
                    {
                        if (!d.Conexoes.Contains(c)) { print(d.name + " " + c.name); d.Conexoes.Add(c); }
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

        ///CONECTOR EM LINHA
        foreach (Connections c in Mconexoes)
        {
            foreach (Connections d in c.Conexoes)
            {


                for (int i = 0; i < 2; i++)
                {
                    Connections c2 = i == 0 ? stc : enc;
                    if (c2 != c && c2 != d)
                    {
                        ///COLISAO LINHA
                        Vector3 AP = c2.transform.position - c.transform.position, AB = d.transform.position - c.transform.position;
                        Vector3 D = c.transform.position + Vector3.Dot(AP, AB) / Vector3.Dot(AB, AB) * AB;

                        if (c.transform.position.x <= d.transform.position.x)
                        {
                            if (D.x >= c.transform.position.x && D.x <= d.transform.position.x && Vector3.Distance(D, c2.transform.position) < 0.1f)
                            {
                                c2.Conexoes.Add(c);
                                c2.Conexoes.Add(d);
                                c.Conexoes.Remove(d);
                                d.Conexoes.Remove(c);
                                goto Clear1; // return false;
                            }
                        }
                        else
                        {
                            if (D.x <= c.transform.position.x && D.x >= d.transform.position.x && Vector3.Distance(D, c2.transform.position) < 0.1f)
                            {
                                c2.Conexoes.Add(c);
                                c2.Conexoes.Add(d);
                                c.Conexoes.Remove(d);
                                d.Conexoes.Remove(c);
                                goto Clear1; // return false;
                            }
                            // return;
                        }
                    }

                }

            }
        }






        //   return true;
    }

    void ClearColisao()
    {
        Clear2:
        ClearNullConnecitons();
        ///LINHA EM LINHA FIX CONTAS
        foreach (Connections c in Mconexoes)
        {
            foreach (Connections d in c.Conexoes)
                foreach (Connections c2 in Mconexoes)
                    if (c != c2 && d != c2 && !c.Conexoes.Contains(c2) && !d.Conexoes.Contains(c2) && !c2.Conexoes.Contains(c) && !c2.Conexoes.Contains(d))
                        foreach (Connections d2 in c2.Conexoes)
                            if (c != d2 && d != d2 && !c.Conexoes.Contains(d2) && !d.Conexoes.Contains(d2) && !d2.Conexoes.Contains(c) && !d2.Conexoes.Contains(d))
                            {

                                float m1 = (d.transform.position.z - c.transform.position.z) / (d.transform.position.x - c.transform.position.x),
                                    m2 = (d2.transform.position.z - c2.transform.position.z) / (d2.transform.position.x - c2.transform.position.x),
                                    b1 = c.transform.position.z - m1 * c.transform.position.x,
                                    b2 = c2.transform.position.z - m2 * c2.transform.position.x;

                                if (m1 != m2)
                                {
                                    float px = (b2 - b1) / (m1 - m2), pz = m1 * px + b1;


                                    if (checkPoint(c2.transform.position.x, d2.transform.position.x, px) && checkPoint(c.transform.position.x, d.transform.position.x, px)) //(stc.transform.position.x <= enc.transform.position.x)
                                    {
                                        print(px + " " + c.transform.position.x);

                                        createReplacement(px, pz, c, d, c2, d2);
                                        goto Clear2; //      return false;
                                                     //  }


                                    }

                                }


                            }

        }
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


    void createReplacement(float px, float pz, Connections c, Connections d, Connections c2, Connections d2)
    {
        GameObject este = Instantiate(Block) as GameObject;
        este.transform.position = new Vector3(px, c.transform.position.y, pz);
        este.name = Mconexoes.Count.ToString();
        Mconexoes.Add(este.GetComponent<Connections>());
        este.GetComponent<Connections>().Conexoes.Add(c);
        este.GetComponent<Connections>().Conexoes.Add(c2);
        este.GetComponent<Connections>().Conexoes.Add(d);
        este.GetComponent<Connections>().Conexoes.Add(d2);

        c.Conexoes.Remove(d);
        d.Conexoes.Remove(c);
        c2.Conexoes.Remove(d2);
        d2.Conexoes.Remove(c2);

        c.Conexoes.Add(este.GetComponent<Connections>());
        d.Conexoes.Add(este.GetComponent<Connections>());
        c2.Conexoes.Add(este.GetComponent<Connections>());
        d2.Conexoes.Add(este.GetComponent<Connections>());
    }

    //float determinant(Vector3 p1, Vector3 p2, Vector3 p3)
    //{
    //    return p1.x * (p2.y * p3.z - p2.z * p3.y) - p2.x * (p3.y * p1.z - p3.z * p1.y) + p3.x * (p1.y * p2.z - p1.z * p2.y);

    //}


    // Connections  In, Out;
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
        foreach (Connections g in Mconexoes)
        {
            foreach (Connections h in g.Conexoes)
            {
                //   float x1 = g.transform.position.x, y1 = g.transform.position.y, x2 = h.transform.position.x, y2 = h.transform.position.y, x3 = p.x, y3 = p.y;
                Vector3 AP = p - g.transform.position, AB = h.transform.position - g.transform.position;
                Vector3 D = g.transform.position + Vector3.Dot(AP, AB) / Vector3.Dot(AB, AB) * AB;
                //g.transform.position + Vector3.Dot(p - g.transform.position, h.transform.position - g.transform.position) /
                // Vector3.Dot(h.transform.position - g.transform.position, h.transform.position - g.transform.position) * h.transform.position - g.transform.position;
                //  print(D);

                if (g.transform.position.x <= h.transform.position.x)
                {
                    if (D.x >= g.transform.position.x && D.x <= h.transform.position.x && Vector3.Distance(D, p) < d)
                    {
                        final = D;
                        d = Vector3.Distance(D, p);
                        // print(g.transform.position);
                        //    bt1 = g;
                        //    bt2 = h;
                    }
                }
                else
                {
                    if (D.x <= g.transform.position.x && D.x >= h.transform.position.x && Vector3.Distance(D, p) < d)
                    {
                        final = D;
                        d = Vector3.Distance(D, p);
                        //    bt1 = g;
                        //     bt2 = h;
                    }
                    // return;
                }

            }
        }

        return final;
    }
    void ShowShader()
    {

    }


}






