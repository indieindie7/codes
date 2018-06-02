     ///DELAUNAY // This is a failed delaunay mesh generator for unity. imma go and start again but in a simpler way
// This was supposed to work and help me generate a city, but sadly it didnt work, i used S-Hull as a source
///http://www.s-hull.org/paper/s_hull.pdf
        List<triangle> trinagulos = new List<triangle>();
        // triangle tg = new triangle(0,1,2);
      ///   retorno:
        for (int i = 0; i < pontos.Count; i++)
        {
            float dist = 10000;
            int perto = i, ck = i;
            //  tg.a = i;
            for (int j = 0; j < pontos.Count; j++)
                if (i != j)
                {
                    if (Vector3.Distance(pontos[i], pontos[j]) < dist)
                    {
                        dist = Vector3.Distance(pontos[i], pontos[j]);
                        perto = j;
                        // tg.b = j;
                    }
                }
            float r = 10000, r2;
            for (int k = 0; k < pontos.Count; k++)
                if (k != i && k != perto && 
                    (!trinagulos.Contains(new triangle(i, perto, k)) || !trinagulos.Contains(new triangle(i, k, perto))
                    || !trinagulos.Contains(new triangle(k, i, perto)) || !trinagulos.Contains(new triangle(k, perto, i))
                    || !trinagulos.Contains(new triangle(perto, i, k)) || !trinagulos.Contains(new triangle(perto, k, i))))
                {
                    r2 = Vector3.Distance(pontos[i], pontos[perto]) / (2 * Mathf.Sin(Vector3.Angle(pontos[i] - pontos[k], pontos[perto] - pontos[k]) * Mathf.Deg2Rad));
                    if (r2 < r) { r = r2; ck = k; } //tg.c = k;
                }
     
            //if (i == 0)
            //{
            //    Vector3 C = Vector3.zero, p1 = pontos[i] / 2 + pontos[perto] / 2, p2 = pontos[i] / 2 + pontos[ck] / 2;
            //    float slope1 = -(pontos[i].z - pontos[perto].z) / (pontos[i].x - pontos[perto].x), slope2 = -(pontos[i].z - pontos[ck].z) / (pontos[i].x - pontos[ck].x);
            //    C.y = pontos[i].y;
            //    C.x = (p2.z - slope2 * p2.x - p1.z + slope1 * p1.x) / (slope1 - slope2);
            //    C.z = slope1 * C.x + p1.z - slope1 * p1.x;
            //    pontos.OrderBy(x => Vector3.Distance(C, x));
            //}
            if (r < 10000)
            {
                trinagulos.Add(new triangle(i, perto, ck));
             ///   goto retorno;
            }
        }

        Mesh mesh2 = new Mesh();
        mesh2.vertices = pontos.ToArray();
        List<int> tris = new List<int>();
        foreach (triangle t in trinagulos)
        {
            tris.Add(t.a);
            tris.Add(t.b);
            tris.Add(t.c);
        }
        mesh2.triangles = tris.ToArray();// triangleIndices;
        mesh2.RecalculateNormals();

        GetComponent<MeshFilter>().mesh = mesh2;
