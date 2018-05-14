using System.Collections;
using System.Collections.Generic;
using UnityEngine;


[System.Serializable]
public struct ExtrudeShape
{
    public Vector2[] vertices;

    public float[] uCoord;
    public int[] triangles;

}


public class RoadDeform : MonoBehaviour
{

    public GameObject g1, g2, g3, g4;
    Vector3[] original;
    Mesh mesh2, mesh;
    public ExtrudeShape shape;

    public float division;
    void Start()
    {


        mesh2 = new Mesh();

        p = new GameObject();
        f = new GameObject();
        f.transform.parent = p.transform;


    }


    GameObject p, f;


    void Update()
    {
        int quantidades = 30;
        Extrude(shape, quantidades);
        GetComponent<MeshFilter>().mesh = mesh2;

    }
    public void Extrude(ExtrudeShape mesh, int quantidades)//, ExtrudeShape shape, OrientedPoint[] path)
    {
        int vertsInShape = mesh.vertices.Length;
        int segments = quantidades;
        int edgeLoops = quantidades;
        int vertCount = vertsInShape * edgeLoops;
        int triCount = (mesh.vertices.Length - 1) * segments;
        int triIndexCount = triCount * 3;

        List<int> triangles = new List<int>();

        List<Vector3> vertices = new List<Vector3>();
        List<Vector2> uvs = new List<Vector2>();
        for (int i = 0; i < quantidades + 1; i++)
        {

            p.transform.position = getPoint((float)i / (float)quantidades);
            p.transform.rotation = getOrientation((float)i / (float)quantidades);


            for (int j = 0; j < vertsInShape; j++)
            {


                f.transform.localPosition = mesh.vertices[j]/division;
                vertices.Add(f.transform.position - transform.position); //+ p.transform.position
           uvs.Add(new Vector2(shape.uCoord[j], Sample( quantidades , (float)i / ((float)edgeLoops) )));
            }
        }


        for (int i = 0; i < quantidades; i++)
        {
            int offset = i * vertsInShape;
            for (int l = 0; l < mesh.triangles.Length; l += 2)
            {
                int a = offset + mesh.triangles[l] + vertsInShape;
                int b = offset + mesh.triangles[l];
                int c = offset + mesh.triangles[l + 1];
                int d = offset + mesh.triangles[l + 1] + vertsInShape;

                triangles.Add(a);
                triangles.Add(b);
                triangles.Add(c);
                triangles.Add(c);
                triangles.Add(d);
                triangles.Add(a);

            }


        }

        mesh2.vertices = vertices.ToArray();
        mesh2.triangles = triangles.ToArray();// triangleIndices;
        mesh2.RecalculateNormals();
         mesh2.uv = uvs.ToArray();

        print(mesh.triangles.Length + " " + mesh.vertices.Length + " " + mesh2.triangles.Length + " " + mesh2.vertices.Length);

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


      float Sample(int quantidades, float t)
    {
        float[] fArr = CalcLengthTableInto(quantidades);
        int count = fArr.Length;
        if (count == 0)
        {
            Debug.LogError("Unable to sample array - it has no elements");
            return 0;
        }
        if (count == 1)
            return fArr[0];
        float iFloat = t * (count - 1);
        int idLower = Mathf.FloorToInt(iFloat);
        int idUpper = Mathf.FloorToInt(iFloat + 1);
        if (idUpper >= count)
            return fArr[count - 1];
        if (idLower < 0)
            return fArr[0];
        return Mathf.Lerp(fArr[idLower], fArr[idUpper], iFloat - idLower);
    }

    float[] CalcLengthTableInto(int quantidades)
    {
        float[] arr = new float[quantidades];
        arr[0] = 0f;
        float totalLength = 0f;
        Vector3 prev = g1.transform.position;
        for (int i = 1; i < arr.Length; i++)
        {
            float t = ((float)i) / (arr.Length - 1);
            Vector3 pt = getPoint(t);
            float diff = (prev - pt).magnitude;
            totalLength += diff;
            arr[i] = totalLength;
            prev = pt;
        }
        return arr;
    }


}
