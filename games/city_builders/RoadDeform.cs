using System.Collections;
using System.Collections.Generic;
using UnityEngine;



public class RoadDeform : MonoBehaviour
{

    public GameObject g1, g2, g3, g4;
  //  public Vector3 p1, p2, p3, p4;
  Vector3[] original;

Mesh mesh2, mesh;

    public GameObject tg;
    void Start()
    {


        mesh = tg.GetComponent<MeshFilter>().mesh;
        mesh2 = new Mesh();

        p = new GameObject();
        f = new GameObject();
        f.transform.parent = p.transform;


    }


    GameObject p, f;


    void Update()
    {
        int quantidades = 30;
        Extrude(mesh, quantidades);
        GetComponent<MeshFilter>().mesh = mesh2;
       
    }
    public void Extrude(Mesh mesh, int quantidades)//, ExtrudeShape shape, OrientedPoint[] path)
    {
        print(mesh.vertices.Length);
        int vertsInShape = mesh.vertices.Length;
        int segments = quantidades ;
        int edgeLoops = quantidades;
        int vertCount = vertsInShape * edgeLoops;
        int triCount = (mesh.vertices.Length - 1) * segments;
        int triIndexCount = triCount * 3;

        print(triCount);
        List<int> triangles = new List<int>();

        List<Vector3> vertices = new List<Vector3>();

        for (int i = 0; i < quantidades + 1; i++)
        {

            p.transform.position = getPoint((float)i / (float)quantidades);
            p.transform.rotation = getOrientation((float)i / (float)quantidades);
            // int offset = i * vertsInShape;
            for (int j = 0; j < vertsInShape; j++)
            {


                f.transform.localPosition = mesh.vertices[j];
                //  int id = offset + j;
                vertices.Add(f.transform.localPosition + p.transform.position - transform.position);

            }
        }
        //int ti = 0;

        for (int i = 0; i < quantidades; i++)
        {
            int offset = i * vertsInShape;
            for (int l = 0; l < mesh.triangles.Length; l += 2)
            {
                int a = offset + mesh.triangles[l] + vertsInShape;
                int b = offset + mesh.triangles[l];
                int c = offset + mesh.triangles[l + 1];
                int d = offset + mesh.triangles[l + 1] + vertsInShape;


                triangles.Add(c);// ti++;
                triangles.Add(b);// ti++;
                triangles.Add(a); // ti++;

                triangles.Add(c);// ti++;
                triangles.Add(a);// ti++;
                triangles.Add(d);// ti++;

            }


        }

        // mesh.Clear();
        mesh2.vertices = vertices.ToArray();
        mesh2.triangles = triangles.ToArray();// triangleIndices;
        mesh2.RecalculateNormals();
        //  mesh2.normals = normals;
        //  mesh2.uv = uvs;



    }


    Vector3 getPoint(float t)
    {
        float omt = 1 - t;
        return omt * omt * omt * g1.transform.position
            + 3 * omt * omt * t * g2.transform.position
            + 3 * omt * t * t * g3.transform.position
            + t * t * t * g4.transform.position;
    }

    Vector3 getUp(float t)
    {
        float omt = 1 - t;
        return omt * omt * omt * g1.transform.up
            + 3 * omt * omt * t * g2.transform.up
            + 3 * omt * t * t * g3.transform.up
            + t * t * t * g4.transform.up;
    }
    Vector3 getTangent(float t)
    {
        float omt = 1 - t;

        return (-g1.transform.position * omt * omt
            + g2.transform.position * (3 * omt * omt - 2 * omt)
            + g3.transform.position * (-3 * t * t + 2 * t)
            + g4.transform.position * t * t
            ).normalized;
    }

    Vector3 getNormal(float t)
    {
        Vector3 tng = getTangent(t);
        Vector3 up = getUp(t);// Vector3.up;// .
        Vector3 binormal = Vector3.Cross(getUp(t), tng).normalized;
        return Vector3.Cross(tng, binormal);

    }

    Quaternion getOrientation(float t)
    {
        Vector3 tng = getTangent(t);
        Vector3 nrm = getNormal(t);
        return Quaternion.LookRotation(tng, nrm);
    }


}
