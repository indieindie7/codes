using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class RoadCreator : MonoBehaviour
{

    public float division;
    public int quantidades;
    Vector3 p1, p2, p3, p4;

    public Material material;

    Mesh mesh2;

    float dist;
    


    public Mesh ExtrudeMesh(TrackShape mesh,  Vector3 t1, Vector3 t2, Vector3 t3, Vector3 t4)
    {
        //print(name);
        mesh2 = new Mesh();
        p1 = t1;//.transform.position;
        p2 = t2;
        p3 = t3;
        p4 = t4;//.transform.position;
        GameObject p = new GameObject();
        GameObject f = new GameObject();
        f.transform.parent = p.transform;
        //   print(mesh.vertices.Length);
        int vertsInShape = mesh.vertices.Length;
        int segments = quantidades;
        int edgeLoops = quantidades;
        int vertCount = vertsInShape * edgeLoops;
        int triCount = (mesh.vertices.Length - 1) * segments;
        int triIndexCount = triCount * 3;

        //  print(triCount);
        List<int> triangles = new List<int>();

        List<Vector3> vertices = new List<Vector3>();
        List<Vector2> uvs = new List<Vector2>();
        //  Vector2[] uvs = new Vector2[vertCount];
        for (int i = 0; i < quantidades + 1; i++)
        {

            p.transform.position = getPoint((float)i / (float)quantidades);
            p.transform.rotation = getOrientation((float)i / (float)quantidades);

            //  int offset = i * vertsInShape;

            for (int j = 0; j < vertsInShape; j++)
            {


                f.transform.localPosition = mesh.vertices[j] / division;
                //  int id = offset + j;
                vertices.Add(f.transform.position); //+ p.transform.position

                //    int id = offset + j;

                uvs.Add(new Vector2(mesh.uCoord[j], Sample(quantidades, (float)i / ((float)edgeLoops))));
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

                triangles.Add(a);
                triangles.Add(b);
                triangles.Add(c);
                triangles.Add(c);
                triangles.Add(d);
                triangles.Add(a);

            }

            // triangles.Add();


        }

        mesh2.vertices = vertices.ToArray();
        mesh2.triangles = triangles.ToArray();// triangleIndices;
        mesh2.RecalculateNormals();
      
        mesh2.uv = uvs.ToArray();
        Destroy(p);

        return mesh2;

    }

    public float getDist()
    {
        return dist;
    }


    Vector3 getPoint(float t)
    {
        float omt = 1 - t;
        return omt * omt * omt * p1
            + 3 * omt * omt * t * p2
            + 3 * omt * t * t * p3
            + t * t * t * p4;
    }

    public Vector3 getPoint2(float t, Vector3 t1, Vector3 t2, Vector3 t3, Vector3 t4)
    {
        float omt = 1 - t;
        return omt * omt * omt * t1
            + 3 * omt * omt * t * t2
            + 3 * omt * t * t * t3
            + t * t * t * t4;
    }


    /// THIS IS A FUNCTION TO GET UP
  /*  Vector3 getUp(float t)
    {
        float omt = 1 - t;
        return omt * omt * omt * g1.transform.up
            + 3 * omt * omt * t * g2.transform.up
            + 3 * omt * t * t * g3.transform.up
            + t * t * t * g4.transform.up;
    } */
    Vector3 getTangent(float t)
    {
        float omt = 1 - t;

        return (-p1 * omt * omt
            + p2 * (3 * omt * omt - 2 * omt)
            + p3 * (-3 * t * t + 2 * t)
            + p4 * t * t
            ).normalized;
    }

    Vector3 getNormal(float t)
    {
        Vector3 tng = getTangent(t);
        Vector3 up = Vector3.up;// getUp(t);//  .
        Vector3 binormal = Vector3.Cross(up, tng).normalized;
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
        Vector3 prev = p1;
        for (int i = 1; i < arr.Length; i++)
        {
            float t = ((float)i) / (arr.Length - 1);
            Vector3 pt = getPoint(t);
            float diff = (prev - pt).magnitude;
            totalLength += diff;
            arr[i] = totalLength;
            prev = pt;
            
        }
        dist = totalLength;
        return arr;
    }

}
